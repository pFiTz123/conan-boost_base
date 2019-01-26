#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import python_requires, python_requires


base = python_requires("boost_base/1.67.0@bincrafters/stable")

class TestPackageConan(base.BoostBaseConan):
    name = "boost_test_package"
    lib_short_names = ["test_package"]
    header_only_libs = ["test_package"]
        
    def test(self):
        pass
