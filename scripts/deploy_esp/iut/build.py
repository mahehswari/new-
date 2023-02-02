# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation

""" SE Install and Upgrade Toolchain build utilities. """

import logging
import os
import subprocess # nosec - B404 (security implications considered)

import iut.slo.system
import iut.error


def make_git_options(git_credentials):
    """ Return a list of deploy_esp.py script options specifying the credentials needed to clone git repositories

        The git credentials should be passed to the deploy_esp.py script using the command-line arguments rather than
        its configuration file to protect the password against being written to disk (deploy_esp.py doesn't log it
        anywhere). If the code would pass them through the provisioning config, they couldn't be anonymized and would
        leak when the user provided the artifacts for inspection.

        Parameters:
            git_credentials - as returned by the iut.config.get_git_credentials function
    """

    opts = []

    if git_credentials["username"]:
        opts += ["--git-user", git_credentials["username"]]

    if git_credentials["password"]:
        opts += ["--git-password", git_credentials["password"]]

    return opts


def build_services(toolchain_cfg: dict, git_credentials: dict, config_path: str):
    """ Builds ESP services to be used during online and offline provisioning

        Parameters:
            toolchain_cfg - install and upgrade toolchain config as provided to the main function
            git_credentials - returned by the iut.config.get_git_credentials function
            config_path - the path to the generated deploy_esp.py configuration
    """

    script_path = os.path.abspath(os.path.join(toolchain_cfg["path"]["full"]["toolchain"], "deploy_esp.py"))
    cmd = [
        "sudo", "-E", script_path, "--log-dir", toolchain_cfg["path"]["full"]["logs"], "--cleanup",
        "--config", config_path] + make_git_options(git_credentials)

    logging.info("Building the ESP services")
    logging.debug(
        "The following command will be executed:\n"
        "    %s", subprocess.list2cmdline(iut.slo.system.clear_password(cmd)))

    try:
        subprocess.run(cmd, check=True) # nosec - B603
    except subprocess.CalledProcessError as e:
        logging.debug(
            "The following Deploy ESP command has failed:\n"
            "    %s", subprocess.list2cmdline(iut.slo.system.clear_password(cmd)))

        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR, "IUT-X",
            "Failed to build the ESP services") from e

    logging.info("The ESP services were built successfully")


def remove_esp_dirs(toolchain_cfg, tmp_root):
    """ Remove temporary directories created by the deploy_esp script which is executed with the root

        The temporary directory cleanup code has failed because of missing privileges
    """

    esp_path = os.path.join(tmp_root, toolchain_cfg["path"]["part"]["tmp"]["esp"])
    out_path = os.path.join(tmp_root, toolchain_cfg["path"]["part"]["tmp"]["esp_out"])

    try:
        subprocess.run( # nosec B603, B607 (the user is the system administrator)
            ["sudo", "rm", "-fr", esp_path, out_path], check=True)
    except subprocess.CalledProcessError as e:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR, "IUT-X",
            f"Failed to remove temporary build directories\n    {e}") from e
