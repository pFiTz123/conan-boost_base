#!/usr/bin/env python3
"""
    Copyright (C) 2019 Rene Rivera.
    Use, modification and distribution are subject to the
    Boost Software License, Version 1.0. (See accompanying file
    LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
"""
import os.path
from pprint import pprint
from bls.git_tool import Git
from bls.util import Main, PushDir
from bls.lib_data import LibraryData


script_dir = os.path.dirname(os.path.realpath(__file__))


class ForEach(Main):
    '''
    Common base that encapsulates executing commands for all the Boost
    packages in correct dependency order.
    '''

    def __init_parser__(self, parser):
        parser.add_argument(
            '++version',
            help='The version of Boost to create.',
            required=True)
        parser.add_argument(
            '++repo-dir',
            help='Directory with local copies of the package sources.',
            required=True)

    def __run__(self):
        label = None
        if self.args.version == 'develop':
            label = 'develop'
        elif self.args.version == 'master':
            label = 'master'
        elif self.args.version:
            label = 'boost-%s' % (self.args.version)
        data_dir = os.path.realpath(os.path.join(
            os.path.dirname(script_dir), '..', 'src', 'data'))
        data_file = os.path.join(data_dir, 'package-data-%s.json' % (label))

        # Generate the build DAG..

        self.package_data = self.__load_data__(data_file)

        # Build simple dependency data.
        package_deps = {}
        # Add the "bootstrap" core dependencies.
        package_deps['build'] = set()
        package_deps['base'] = set(['build'])
        #
        for lib, info in self.package_data.items():
            # All packages depend on the base.
            lib_deps = set(['base'])
            # Add regular and build only deps.
            lib_deps |= set(info['b2_requires'])
            lib_deps |= set(info['source_only_deps'])
            # Record the deps.
            package_deps[lib] = lib_deps

        # Generate build groups in DAG order by decimating the deps graph.
        groups = []
        while len(package_deps) > 0:
            # Each group contains all the packages that have no deps.
            group = set()
            for package, deps in package_deps.items():
                if len(deps) == 0:
                    group.add(package)
            groups.append(group)
            print(">>>> GROUP: %s" % (group))
            if len(group) == 0:
                pprint(package_deps)
                exit(1)
            # We now remove the group members as they are accounted for.
            for package in group:
                del package_deps[package]
            # Decimate the graph to remove this group.
            for package in package_deps.keys():
                package_deps[package] -= group

        # We can now go through the groups in the DAG order. But do it by
        # some method calls to allow customizing any part of the
        # process.
        with PushDir(self.args.repo_dir) as _:
            os.environ['CONAN_VERBOSE_TRACEBACK'] = '1'
            self.groups_pre(groups)
            self.groups_foreach(groups)
            self.groups_post(groups)

    def groups_pre(self, groups):
        for group in groups:
            self.group_pre(group)

    def groups_foreach(self, groups):
        for group in groups:
            self.group_foreach(group)

    def groups_post(self, groups):
        for group in groups:
            self.group_post(group)

    def group_pre(self, group):
        for package in group:
            self.package_pre(package)

    def group_foreach(self, group):
        for package in group:
            self.package_do(package)

    def group_post(self, group):
        for package in group:
            self.package_post(package)

    def package_pre(self, package):
        pass

    def package_do(self, package):
        pass

    def package_post(self, package):
        pass


class CreateAll(ForEach):
    '''
    Creates, i.e. "conan create", all the Boos packages possible.
    '''

    def groups_pre(self, groups):
        self.__check_call__([
            'conan', 'remove', '-f', 'boost_*'
        ])
        super(CreateAll, self).groups_pre(groups)

    def package_do(self, package):
        super(CreateAll, self).package_do(package)
        if package == 'base':
            with PushDir(os.path.dirname(os.path.dirname(script_dir))) as _:
                self.__check_call__([
                    'conan', 'create', '.', 'bincrafters/testing'
                ])
        else:
            if os.path.isdir(package):
                self.__check_call__([
                    'conan', 'create', package, 'bincrafters/testing'
                ])


if __name__ == "__main__":
    CreateAll()
