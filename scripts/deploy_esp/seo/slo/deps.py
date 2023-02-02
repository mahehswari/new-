# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

""" Special purpose module defining a function used to check if some third-party dependencies are fulfilled by the
    environment the script is executed in.

    Warning:
        This module mustn't directly or indirectly import any third-party modules (i.e., modules that aren't part of
        the Python standard library otherwise the program will fail before it can handle missing dependencies
        gracefully.
"""

import os
import sys

import pkg_resources

import seo.slo.error


# Default requirements file covering the seo module and the scripts from the deploy_esp family (deploy_esp.py, and
#  flash_usb.py):
_SEO_REQUIREMENTS=os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "..", "..", "seo_requirements.txt")


def load(requirements_path):
    """ Load requirement specifiers from given requirements file and return it as a list of specifier strings ready to
        be passed to the pkg_resources.require function

        Parameters:
            requirements_path - path to the requirements file to be loaded
    """

    with open(requirements_path) as f:
        lines = f.readlines()

    return [str(r) for r in pkg_resources.parse_requirements(lines)]


def verify(requirements_path=_SEO_REQUIREMENTS):
    """ Verify if all the provided requirements are fulfilled by the current environment

        Parameters:
            requirements_path - path to the requirements file to be loaded
    """

    requirements = load(requirements_path)

    try:
        pkg_resources.require(requirements)
    except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict) as e:
        sys.stderr.write(
            "ERROR: Required Python dependencies are not installed\n"
            f"    {e}\n\n"
            f"    {seo.slo.error.TS_REF}\n")
        sys.exit(seo.slo.error.Codes.MISSING_PREREQUISITE.value)
