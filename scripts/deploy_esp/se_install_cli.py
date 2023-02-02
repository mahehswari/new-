# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
SE Install and Upgrade Toolchain: Full provisioning (OS installation and SE deployment) control script
"""

import argparse
import tempfile
import logging

import iut.build
import iut.config
import iut.error
import iut.install
import iut.monitoring
import iut.run
import iut.services

import hooks.install # pylint: disable=import-error,wrong-import-order

def parse_args(package_root, toolchain_cfg):
    """ Parse script arguments """
    product_name = toolchain_cfg["product"]["name"]

    p = argparse.ArgumentParser(
        add_help=False,
        description=f"Install the {product_name} according to the configuration provided")

    g = p.add_argument_group("install arguments")

    g.add_argument(
        "--image-url", action="store", dest="image_url", metavar="URL", required=False,
        help="Custom URL to the image hosted on HTTP/HTTPS web server")

    iut.config.create_common_argument_group(p, package_root)
    iut.config.create_auth_argument_group(p, toolchain_cfg)

    args = p.parse_args()
    args.prog = p.prog

    return args


def main(args, toolchain_cfg):
    """ Script entry function """

    platform_cfg = iut.config.load_platform_cfg(args, toolchain_cfg)

    tmp_root = tempfile.mkdtemp(dir=args.tmp_dir_path)

    logging.info("Working in %s mode", "offline" if toolchain_cfg["context"]["offline_flag"] else "online")

    hooks.install.init(toolchain_cfg, platform_cfg)

    if not toolchain_cfg["context"]["offline_flag"]:
        iut.monitoring.build_service(toolchain_cfg)
    monitoring_service = iut.monitoring.run_service()
    machines = iut.monitoring.extract_machine_list(platform_cfg)
    machines = iut.monitoring.retrieve_machine_data(machines)
    iut.monitoring.register_machines(machines, monitoring_service)

    provisioning_cfg_path = iut.config.generate_provisioning_config(
        toolchain_cfg, platform_cfg, args, tmp_root, machines)

    git_creds = iut.config.get_git_credentials(platform_cfg, args)
    # TODO: The services should only be built in the online mode:
    iut.build.build_services(toolchain_cfg, git_creds, provisioning_cfg_path)

    iut.services.run_esp_services(toolchain_cfg, git_creds, provisioning_cfg_path)

    iut.install.start(toolchain_cfg, platform_cfg, args, machines, monitoring_service)

    iut.config.copy_ssh_keys_to_hosts(platform_cfg)
    iut.config.generate_deployment_configuration(toolchain_cfg, platform_cfg)
    iut.services.run_ansible_deployment(toolchain_cfg, platform_cfg)

    iut.services.stop_esp_services(toolchain_cfg, provisioning_cfg_path)
    iut.build.remove_esp_dirs(toolchain_cfg, tmp_root)

    logging.info("Provisioning finished successfully")

    return iut.error.Codes.NO_ERROR


def run_main(toolchain_cfg):
    """ Convenience entry function wrapper to be called from the top-most se_install.py script """
    iut.run.run(main, parse_args, toolchain_cfg)
