#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Smart Edge Platform Configuration utility script wrapper acting as a source of experience kit specific configuration
variables shared by the adjacent se_*.py scripts
"""

import os
import sys
import copy

import se_context


def add_import_path(toolchain_cfg):
    """ Add the toolchain path to the python import path to allow importing of the toolchain modules """
    repo_path = toolchain_cfg["path"]["full"]["repo"]
    sys.path.insert(1, os.path.join(repo_path, toolchain_cfg["path"]["part"]["toolchain"]))
    sys.path.insert(1, os.path.join(repo_path, toolchain_cfg["path"]["part"]["hooks"]))


def get_toolchain_cfg():
    """ Return toolchain configuration data """
    package_root = os.path.dirname(os.path.realpath(__file__))
    config_toolchain = copy.deepcopy(se_context.TOOLCHAIN_CFG)
    config_toolchain["path"]["full"]["repo"] = package_root
    return config_toolchain


if __name__ == "__main__":
    CFG = get_toolchain_cfg()
    add_import_path(CFG)
    import iut.slo.deps # pylint: disable=import-error, E0611
    iut.slo.deps.check_deps(CFG) # pylint: disable=no-member
    import se_config_cli # pylint: disable=import-error
    se_config_cli.run_main(CFG)
