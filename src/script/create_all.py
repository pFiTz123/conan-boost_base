#!/usr/bin/env python3
"""
    Copyright (C) 2019 Rene Rivera.
    Use, modification and distribution are subject to the
    Boost Software License, Version 1.0. (See accompanying file
    LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
"""
import os.path
import sys
from pprint import pprint
from bls.util import PushDir
from foreach import ForEach


script_dir = os.path.dirname(os.path.realpath(__file__))


class CreateAll(ForEach):
    '''
    Creates, i.e. "conan create", all the Boos packages possible.
    '''

    def __init_parser__(self, parser):
        super(CreateAll, self).__init_parser__(parser)
        parser.add_argument(
            'create',
            help='Arguments to pass to the "conan create" invocations.',
            nargs='*',
            default=[])

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
                ]+self.args.create)
        else:
            if os.path.isdir(package):
                self.__check_call__([
                    'conan', 'create', package, 'bincrafters/testing'
                ]+self.args.create)


if __name__ == "__main__":
    CreateAll()
