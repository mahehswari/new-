# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Various shell helpers
"""

import logging
import os
import subprocess # nosec - B404 (security implications considered)

import iut.error


def get_user_group():
    """ Retrieve the effective primary group of the current user """
    cmd = ["id", "-gn"]

    try:
        cp = subprocess.run( # nosec - B603 (subprocess call)
            cmd, stdout=subprocess.PIPE, universal_newlines=True, check=True)
    except subprocess.CalledProcessError as e:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR,
            "IUT-X",
            "Failed to determine the current user primary group name:\n"
            "    The following command has failed:\n"
            f"        {subprocess.list2cmdline(cmd)}") from e

    return cp.stdout.strip()


def get_user_name():
    """ Retrieve the name of the current user """

    # The function could retrieve the user name from the 'USER' environment variable, but this could be overwritten by
    #  the user, also to something invalid. To be sure that it is valid and to behave consistently with the
    #  'get_user_group' function, let's use the 'id' command also in this case:

    cmd = ["id", "-un"]

    try:
        cp = subprocess.run( # nosec - B603 (subprocess call)
            cmd, stdout=subprocess.PIPE, universal_newlines=True, check=True)
    except subprocess.CalledProcessError as e:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR,
            "IUT-X",
            "Failed to determine the current user name\n"
            "    The following command has failed:\n"
            f"        {subprocess.list2cmdline(cmd)}") from e

    return cp.stdout.strip()


def set_dir_ownership(path, user, group):
    """ Recursively change the owner user and group of a directory """

    cmd = ["sudo", "chown", "--recursive", f"{user}:{group}", path]

    try:
        subprocess.run(cmd, check=True) # nosec - B603 (subprocess call)
    except subprocess.CalledProcessError as e:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR,
            "IUT-X",
            f"Failed to set the '{os.path.relpath(path)}' directory ownership:\n"
            "    The following command has failed:\n"
            f"        {subprocess.list2cmdline(cmd)}") from e

    logging.debug("Set the '%s' directory ownership to '%s:%s'", os.path.relpath(path), user, group)
