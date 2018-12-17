#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, tools
import os


class BoostBaseConan(ConanFile):
    name = "boost_base"
    version = "1.69.0"
    url = "https://github.com/bincrafters/conan-boost_base"
    website = "https://github.com/boostorg"
    description = "Shared python code used in other Conan recipes for the Boost libraries"
    license = "MIT"
    exports = "LICENSE.md"
    short_paths = True
    build_requires = "boost_generator/1.69.0@bincrafters/testing"
    settings = "os", "arch", "compiler", "build_type"
    generators = "boost"
    
    def boost_init(self):
        if not hasattr(self, "lib_short_names"):
            self.lib_short_names = []
        if not hasattr(self, "source_only_deps"):
            self.source_only_deps = []
        if not hasattr(self, "header_only_libs"):
            self.header_only_libs = []
        if not hasattr(self, "cycle_group"):
            self.cycle_group = ""
        if not hasattr(self, "b2_requires"):
            self.b2_requires = []
        if not hasattr(self, "b2_build_requires"):
            self.b2_build_requires = []
        if not hasattr(self, "b2_defines"):
            self.b2_defines = []
        if not hasattr(self, "b2_options"):
            self.b2_options = self.get_b2_options()
    
    def is_in_cycle_group(self):
        return self.cycle_group != ""
        
    def is_cycle_group(self):
        return (("level" in self.name and "group" in self.name) or ("cycle_group" in self.name))
    
    def lib_name(self):
        return self.lib_short_names[0] if not self.is_cycle_group() and self.lib_short_names else ""

    def is_header_only(self, lib_name):
        return (lib_name in self.header_only_libs)
        
    def get_b2_options(self):
        return {}
        
    jam_header_only_content = """\
import project ;
import path ;
import modules ;
ROOT({lib_short_name}) = [ path.parent [ path.parent [ path.make [ modules.binding $(__name__) ] ] ] ] ;
project /conan/{lib_short_name} : requirements <include>$(ROOT({lib_short_name}))/include ;
project.register-id /boost/{lib_short_name} : $(__name__) ;\
"""

    jam_search_content = """\
lib {lib_link_name} : : <name>{lib_link_name} <search>. : : $(usage) ;
"""
        
    jam_alias_content = """\
alias boost_{lib_short_name} : {space_joined_libs} : : : $(usage) ;
"""

    def all_b2_args(self):
        option_str = " " .join([key + "=" + value for key,value in self.b2_options.items()])
        define_str = " " .join(["define=" + define for define in self.b2_defines])
        include_str = " " .join(["include=" + lib + '/include' for lib in self.source_only_deps])
        return " ".join([option_str, include_str, define_str])
    
    def configure(self):
        self.configure_additional()
    
    def configure_additional(self):
        pass
        
    def requirements(self):
        self.boost_init()
        for dep in self.b2_requires:
            self.requires("{dep}/{ver}@{user}/{channel}".format(
                    dep=dep,
                    ver=self.version,
                    user=self.user,
                    channel=self.channel,
            ))
            
        self.requirements_additional()
        
    def requirements_additional(self):
        pass
        
    def build_requirements(self):
        self.boost_init()
        for dep in self.b2_build_requires:
            self.build_requires("{dep}/{ver}@{user}/{channel}".format(
                    dep=dep,
                    ver=self.version,
                    user=self.user,
                    channel=self.channel,
            ))
            
        self.build_requirements_additional()
        
    def build_requirements_additional(self):
        pass
    
    def source(self):
        self.boost_init()
        if self.is_cycle_group():
            self._source_common()
        elif self.is_in_cycle_group():
            pass
        else:
            self._source_common()
                           
        self.source_additional()
        
    def _source_common(self):
        archive_name = "boost-" + self.version
        libs_to_get = self.lib_short_names + self.source_only_deps
        for lib_short_name in libs_to_get:
            tools.get("{0}/{1}/archive/{2}.tar.gz"
                .format(self.website, lib_short_name, archive_name))
            os.rename(lib_short_name + "-" + archive_name, lib_short_name)
                
    def source_additional(self):
        pass

    def build(self):
        self.boost_init()
        if self.is_cycle_group():
            self._build_common()
        elif self.is_in_cycle_group():
            pass
        else:
            self._build_common()
            
        self.build_additional()
            
    def _build_common(self):
        for lib_short_name in self.lib_short_names:
            lib_dir = os.path.join(lib_short_name, "lib")
            jam_file = os.path.join(lib_dir, "jamroot.jam")
            if self.is_header_only(lib_short_name):
                header_only_content = self.jam_header_only_content.format(
                    lib_short_name=lib_short_name)
                tools.save(jam_file, header_only_content,append=True) 
            else:
                b2_command = [ 
                    "b2",
                    "-j%s" % (tools.cpu_count()),
                    "-d+%s" % (os.getenv('CONAN_B2_DEBUG', '1')),
                    "-a", "--hash=yes", "--debug-configuration", "--layout=system",
                    self.all_b2_args(),
                    lib_short_name + "-build",
                ]
                self.output.info("%s: %s" % (os.getcwd(), " ".join(b2_command)))
                with tools.environment_append({'PATH':[os.getenv('MPI_BIN', '')]}):
                    self.run(" ".join(b2_command))
                
                libs = self._collect_build_libs(lib_dir)
                for lib in libs:
                    search_content = self.jam_search_content.format(
                            lib_link_name=lib)
                    tools.save(jam_file, search_content, append=True) 
                
                if "boost_" + lib_short_name not in libs:
                    alias_content = self.jam_alias_content.format(
                            lib_short_name=lib_short_name, 
                            space_joined_libs=" ".join(libs))
                    tools.save(jam_file, alias_content, append=True) 
                        
    def _collect_build_libs(self, lib_folder):
        libs = []
        if not os.path.exists(lib_folder):
            self.output.warn("Lib folder doesn't exist, can't collect libraries: {0}".format(lib_folder))
        else:
            files = os.listdir(lib_folder)
            for f in files:
                name, ext = os.path.splitext(f)
                if ext in (".so", ".lib", ".a", ".dylib"):
                    if ext != ".lib" and name.startswith("lib"):
                        name = name[3:]
                    libs.append(name)
        return libs
 
    def build_additional(self):
        pass
        
    def package(self):
        self.boost_init()
        for lib_short_name in self.lib_short_names:
            self.copy(pattern="*LICENSE*", dst="license", src=lib_short_name)
            for subdir in ["lib", "include"]:
                copydir = os.path.join(lib_short_name, subdir)
                self.copy(pattern="*", dst=copydir, src=copydir)
  
        self.package_additional()

    def package_additional(self):
        pass
        
    def package_info(self):
        self.boost_init()
        self.user_info.lib_short_names = ",".join(self.lib_short_names)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        
        if self.is_cycle_group():
            for lib_short_name in self.lib_short_names:
                lib_dir = os.path.join(lib_short_name, "lib")
                self.cpp_info.libdirs.append(lib_dir)
                include_dir = os.path.join(lib_short_name, "include")
                self.cpp_info.includedirs.append(include_dir)
        elif self.is_in_cycle_group():
            group = self.deps_cpp_info[self.cycle_group]
            include_dir = os.path.join(group.rootpath, self.lib_name(), "include")
            self.cpp_info.includedirs.append(include_dir)
            lib_dir = os.path.join(group.rootpath, self.lib_name(), "lib")
            self.cpp_info.libdirs.append(lib_dir)
            if not self.is_header_only(self.lib_name()):
                self.cpp_info.libs.extend(tools.collect_libs(self, lib_dir))
        else:
            include_dir = os.path.join(self.lib_name(), "include")
            self.cpp_info.includedirs.append(include_dir)
            lib_dir = os.path.join(self.lib_name(), "lib")
            self.cpp_info.libdirs.append(lib_dir)
            if not self.is_header_only(self.lib_name()):
                self.cpp_info.libs.extend(tools.collect_libs(self, lib_dir))
    
        self.cpp_info.defines.append("BOOST_ALL_NO_LIB=1")
        self.cpp_info.bindirs.extend(self.cpp_info.libdirs)
        # Avoid duplicate entries in the libs.
        self.cpp_info.libs = list(set(self.cpp_info.libs))    
        
        self.package_info_additional()
        
    def package_info_additional(self):
        pass
        
    def package_id(self):
        if self.__class__.__name__ == "BoostBaseConan":
            self.info.header_only()
        else:
            self.boost_init()
            if self.is_header_only(self.lib_name()):
                self.info.header_only()

            boost_deps_only = [dep_name for dep_name in self.info.requires.pkg_names if dep_name.startswith("boost_")]

            for dep_name in boost_deps_only:
                self.info.requires[dep_name].full_version_mode()
                    
            self.package_id_additional()
            
    def package_id_additional(self):
        pass
            


