# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation

""" SE Install and Upgrade Toolchain run services utilities. """

import logging
import os
import subprocess # nosec - B404 (security implications considered)

import iut.error
import iut.slo.system
import iut.build


def run_esp_services(toolchain_cfg: dict, git_credentials: dict, config_path: str):
    """ Runs ESP services to be used during online and offline provisioning

        Parameters:
            toolchain_cfg - install and upgrade toolchain config as provided to the main function
            git_credentials - returned by the iut.config.get_git_credentials function
            config_path - the path to the generated deploy_esp.py configuration
    """

    script_path = os.path.relpath(os.path.join(toolchain_cfg["path"]["full"]["toolchain"], "deploy_esp.py"))
    cmd = [
        "sudo", "-E", script_path, "--log-dir", toolchain_cfg["path"]["full"]["logs"], "-c", config_path,
        "--run-esp-for-usb-boot"] + iut.build.make_git_options(git_credentials)

    logging.info("Starting the ESP services")
    logging.debug(
        "The following command will be executed:\n"
        "    %s", subprocess.list2cmdline(iut.slo.system.clear_password(cmd)))

    try:
        subprocess.run(cmd, check=True) # nosec - B603
    except subprocess.CalledProcessError as e:
        logging.debug(
            "The following command has failed:\n"
            "    %s", subprocess.list2cmdline(iut.slo.system.clear_password(cmd)))

        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR, "IUT-X",
            "Failed to run the ESP services") from e

    logging.info("The ESP services were run successfully")


def stop_esp_services(toolchain_cfg, config_path):
    """ Stops ESP services with toolchain configuration data specified as toolchain_cfg and configuration data path
        specified as config_path"""

    script = os.path.relpath(os.path.join(toolchain_cfg["path"]["full"]["toolchain"], "deploy_esp.py"))
    cmd = [
        "sudo", "-E", script, "--log-dir", toolchain_cfg["path"]["full"]["logs"], "-c", config_path,
        "--stop-esp"]

    logging.debug("Stopping ESP services")

    try:
        subprocess.run(cmd, check=True) # nosec - B603
    except subprocess.CalledProcessError as e:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR, "IUT-X",
            f"Failed to stop the provisioning services\n    {subprocess.list2cmdline(cmd)}") from e

    logging.info("The provisioning services were stopped successfully")


def run_ansible_deployment(toolchain_cfg, platform_cfg):
    """ Start the deployment process """

    root = toolchain_cfg["path"]["full"]["repo"]
    experience_kit_path = os.path.join(root, platform_cfg["experience_kits"][0]["path"])

    cmd = [os.path.join(experience_kit_path, "deploy.py"), "-S"]

    logging.debug(
        "Running experience kit deployment:\n"
        "    %s", subprocess.list2cmdline(cmd))

    try:
        subprocess.run(cmd, check=True) # nosec - B603
    except subprocess.CalledProcessError as e:
        logging.debug(
            "The following experience kit deployment command has failed:\n"
            "    %s", subprocess.list2cmdline(cmd))

        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR,
            "IUT-X",
            "Failed to deploy experience kit") from e
