from conans import ConanFile, tools
import os


def b2_options(conanfile, lib_name=None):
    result = ""
    if hasattr(conanfile, 'b2_options'):
        result += conanfile.b2_options(lib_name=lib_name)
    for lib in source_only_deps(conanfile, lib_name):
        result += ' include=' + lib + '/include'
    return result


def is_header_only(conanfile, lib_name=None):
    try:
        if type(conanfile.is_header_only) == bool:
            return conanfile.is_header_only
        elif lib_name:
            return conanfile.is_header_only[lib_name]
        else:
            for lib_name in conanfile.lib_short_names:
                if not is_header_only(conanfile, lib_name):
                    return False
    except Exception:
        pass
    return True


def source_only_deps(conanfile, lib_name):
    try:
        return list(conanfile.source_only_deps[lib_name])
    except Exception:
        pass
    try:
        return list(conanfile.source_only_deps)
    except Exception:
        pass
    return []


def is_in_cycle_group(conanfile):
    try:
        return hasattr(conanfile, "level_group") 
    except Exception:
        return False


def is_cycle_group(conanfile):
    try:
        return conanfile.is_cycle_group
    except Exception:
        return False


def source(conanfile):
    # print(">>>>> conanfile.source: " + str(conanfile))
    if not is_in_cycle_group(conanfile):
        boostorg_github = "https://github.com/boostorg"
        archive_name = "boost-" + conanfile.version
        # archive_name = "master"
        libs_to_get = list(conanfile.lib_short_names)
        for lib_short_name in conanfile.lib_short_names:
            libs_to_get.extend(source_only_deps(conanfile, lib_short_name))
        for lib_short_name in libs_to_get:
            tools.get("{0}/{1}/archive/{2}.tar.gz"
                .format(boostorg_github, lib_short_name, archive_name))
            os.rename(lib_short_name + "-" + archive_name, lib_short_name)


def collect_build_libs(conanfile, lib_folder):
    if not os.path.exists(lib_folder):
        conanfile.output.warn("Lib folder doesn't exist, can't collect libraries: {0}".format(lib_folder))
        return []
    files = os.listdir(lib_folder)
    result = []
    for f in files:
        name, ext = os.path.splitext(f)
        if ext in (".so", ".lib", ".a", ".dylib"):
            if ext != ".lib" and name.startswith("lib"):
                name = name[3:]
            result.append(name)
    return result


def build(conanfile):
    # print(">>>>> conanfile.build: " + str(conanfile))
    for lib_short_name in conanfile.lib_short_names:
        lib_dir = os.path.join(lib_short_name, "lib")
        if is_header_only(conanfile, lib_short_name):
            if not is_cycle_group(conanfile):
                if not os.path.exists(lib_dir):
                    os.makedirs(lib_dir)
                with open(os.path.join(lib_dir, "jamroot.jam"), "w") as f:
                    f.write("""\
import project ;
import path ;
import modules ;
ROOT({0}) = [ path.parent [ path.parent [ path.make [ modules.binding $(__name__) ] ] ] ] ;
project /conan/{0} : requirements <include>$(ROOT({0}))/include ;
project.register-id /boost/{0} : $(__name__) ;\
""".format(lib_short_name))
        elif not is_in_cycle_group(conanfile):
            b2_command = [ "b2",
                "-j%s" % (tools.cpu_count()),
                "-d+%s" % (os.getenv('CONAN_B2_DEBUG', '1')),
                "-a", "--hash=yes", "--debug-configuration", "--layout=system",
                b2_options(conanfile, lib_short_name),
                "%s-build" % (lib_short_name),
                ]
            conanfile.output.info("%s: %s" % (os.getcwd(), " ".join(b2_command)))
            with tools.environment_append({'PATH':[os.getenv('MPI_BIN', '')]}):
                conanfile.run(" ".join(b2_command))
            libs = collect_build_libs(conanfile, lib_dir)
            with open(os.path.join(lib_dir, "jamroot.jam"), "a") as f:
                for lib in libs:
                    f.write("""\
lib {0} : : <name>{0} <search>. : : $(usage) ;
""".format(lib))
                if "boost_" + lib_short_name not in libs:
                    f.write("""\
alias boost_{0} : {1} : : : $(usage) ;
""".format(lib_short_name, " ".join(libs)))


def package(conanfile, *subdirs_to_package):
    # print(">>>>> conanfile.package: " + str(conanfile))
    if not subdirs_to_package:
        subdirs_to_package = []
    subdirs_to_package.extend(["lib", "include"])
    for lib_short_name in conanfile.lib_short_names:
        conanfile.copy(pattern="*LICENSE*", dst="license", src=lib_short_name)
        for subdir in subdirs_to_package:
            copydir = os.path.join(lib_short_name, subdir)
            conanfile.copy(pattern="*", dst=copydir, src=copydir)


def package_info(conanfile):
    # print(">>>>> conanfile.package_info: " + str(conanfile))
    conanfile.user_info.lib_short_names = ",".join(conanfile.lib_short_names)
    conanfile.cpp_info.includedirs = []
    conanfile.cpp_info.libdirs = []
    conanfile.cpp_info.bindirs = []
    conanfile.cpp_info.libs = []
    if is_in_cycle_group(conanfile):
        lib_name = conanfile.lib_short_names[0]
        group = conanfile.deps_cpp_info[conanfile.level_group]
        include_dir = os.path.join(group.rootpath, lib_name, "include")
        lib_dir = os.path.join(group.rootpath, lib_name, "lib")
        conanfile.cpp_info.includedirs.append(include_dir)
        if not is_header_only(conanfile):
            conanfile.cpp_info.libdirs.append(lib_dir)
            conanfile.cpp_info.bindirs.append(lib_dir)
            conanfile.cpp_info.libs.extend(tools.collect_libs(conanfile, lib_dir))
    elif is_cycle_group(conanfile):
        for lib_short_name in conanfile.lib_short_names:
            lib_dir = os.path.join(lib_short_name, "lib")
            conanfile.cpp_info.libdirs.append(lib_dir)
            include_dir = os.path.join(lib_short_name, "include")
            conanfile.cpp_info.includedirs.append(include_dir)
    else:
        for lib_short_name in conanfile.lib_short_names:
            lib_dir = os.path.join(lib_short_name, "lib")
            conanfile.cpp_info.libdirs.append(lib_dir)
            conanfile.cpp_info.libs.extend(tools.collect_libs(conanfile, lib_dir))
            include_dir = os.path.join(lib_short_name, "include")
            conanfile.cpp_info.includedirs.append(include_dir)
    conanfile.cpp_info.defines.append("BOOST_ALL_NO_LIB=1")
    conanfile.cpp_info.bindirs.extend(conanfile.cpp_info.libdirs)
    # Avoid duplicate entries in the libs.
    conanfile.cpp_info.libs = list(set(conanfile.cpp_info.libs))
