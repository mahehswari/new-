# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Configuration related utilities

Warning:
    This module is a part of the Standard Library Only (SLO) submodule, and as such, it mustn't directly or indirectly
    import any third-party modules (i.e., modules that aren't part of the Python standard library)
"""

import copy
import os


def add_debug_argument(dest):
    """ Add the debug argument to the provided argparse object (parser or argument group object) """

    dest.add_argument(
        "--debug", action="store_true", dest="debug",
        help="provide more verbose diagnostic information")


def add_help_argument(dest):
    """ Add the help argument to the provided argparse object (parser or argument group object) """

    dest.add_argument("-h", "--help", action="help", help="show this help message and exit")


def augment_toolchain_cfg(toolchain_cfg):
    """ Augment the toolchain configuration data taken from the repository root (se_context.py file) to add some
        commonly used data transformations to it (e.g., joining path components to create full paths) and some
        bits of default configuration that most probably will always be the same
    """
    cfg = copy.deepcopy(toolchain_cfg)

    # Transformed configuration:
    cfg["path"]["full"]["primary_ek"] = os.path.normpath(
        os.path.join(cfg["path"]["full"]["repo"], cfg["path"]["part"]["scripts"], ".."))
    cfg["path"]["full"]["toolchain"] = os.path.join(cfg["path"]["full"]["repo"], cfg["path"]["part"]["toolchain"])
    cfg["path"]["full"]["logs"] = os.path.join(cfg["path"]["full"]["repo"], cfg["path"]["part"]["logs"])
    cfg["prog"] = None # Will be updated in the iut.run.run function after the CLI args are parsed

    # Default configuration:
    cfg["path"]["part"].setdefault("tmp", {}).setdefault("esp", "esp")
    cfg["path"]["part"]["tmp"].setdefault("esp_out", "deploy_esp_out")

    return cfg
