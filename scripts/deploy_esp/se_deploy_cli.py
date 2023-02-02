# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
SE Install and Upgrade Toolchain: Deployment-only control script
"""

import argparse
import logging

import iut.config
import iut.error
import iut.monitoring
import iut.run
import iut.services
import iut.checksum

def parse_args(package_root, toolchain_cfg):
    """ Parse script arguments """
    product_name = toolchain_cfg["product"]["name"]

    p = argparse.ArgumentParser(
        add_help=False,
        description=f"Deploy the {product_name} according to the configuration provided")

    iut.config.create_common_argument_group(p, package_root)

    args = p.parse_args()
    args.prog = p.prog
    return args


def main(args, toolchain_cfg):
    """ Script entry function """

    platform_cfg = iut.config.load_platform_cfg(args, toolchain_cfg)

    logging.info("Working in %s mode", "offline" if toolchain_cfg["context"]["offline_flag"] else "online")

    if toolchain_cfg["context"]["offline_flag"]:
        iut.checksum.verify_checksum_files(toolchain_cfg)

    if not toolchain_cfg["context"]["offline_flag"]:
        iut.monitoring.build_service(toolchain_cfg)
    iut.monitoring.run_service()

    iut.config.copy_ssh_keys_to_hosts(platform_cfg)
    iut.config.generate_deployment_configuration(toolchain_cfg, platform_cfg)
    iut.services.run_ansible_deployment(toolchain_cfg, platform_cfg)

    logging.info("Deployment finished successfully")

    return iut.error.Codes.NO_ERROR


def run_main(toolchain_cfg):
    """ Convenience entry function wrapper to be called from the top-most se_deploy.py script """
    iut.run.run(main, parse_args, toolchain_cfg)
