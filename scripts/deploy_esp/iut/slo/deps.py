# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Special purpose module defining a function used to check if some third-party dependencies are fulfilled by the
environment the script is executed in.

Warning:
    This module is a part of the Standard Library Only (SLO) submodule, and as such, it mustn't directly or indirectly
    import any third-party modules (i.e., modules that aren't part of the Python standard library)
"""

import os
import sys

import pkg_resources


def load(toolchain_cfg):
    """ Load requirement specifiers from given requirements file and return it as a list of specifier strings ready to
        be passed to the pkg_resources.require function

        Parameters:
            requirements_path - path to the requirements file to be loaded

        Warning:
            Don't emit logs in this function, as it will cause duplicate log entries to be printed to the screen.
    """

    visited_files = []
    def _load(requirements_path):
        """ Loads requirement files recursively when the line contains `-r` """
        with open(requirements_path) as f:
            lines = f.readlines()

        # protection against getting into an endless loop of opening the same files
        visited_files.append(os.path.realpath(requirements_path))
        if len(visited_files) != len(set(visited_files)):
            sys.stderr.write(
                f"{os.path.basename(__file__)}: [ERROR] Requirements files refer to each other or "
                "want to load a file that was previously loaded.\n")
            sys.exit(1)

        root_path = os.path.dirname(requirements_path)

        packages = []
        for i in lines:
            if i.startswith("-r "):
                # All the links are relative to the currently processed requirements file. This is how pip install -r
                # works:
                path = os.path.join(root_path, i.lstrip("-r ").rstrip("\n"))
                packages.extend(_load(path))
                continue
            packages.append(i)
        return packages

    requirements = _load(
        os.path.join(toolchain_cfg["path"]["full"]["repo"], toolchain_cfg["path"]["part"]["dependencies"]))
    return [str(r) for r in pkg_resources.parse_requirements(requirements)]


def check_deps(toolchain_cfg):
    """ Verify if all the provided requirements are fulfilled by the current environment

        Parameters:
            toolchain_cfg - toolchain configuration data to be loaded

        Warning:
            Don't emit logs in this function, as it will cause duplicate log entries to be printed to the screen.
    """

    requirements = load(toolchain_cfg)

    try:
        pkg_resources.require(requirements)
    except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict) as e:
        sys.stderr.write(
            f"{os.path.basename(__file__)}: [ERROR] Required Python dependencies are not installed\n"
            f"    {e}\n")
        sys.exit(1)
