# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
SE Report command providing a method to collect all the installation related logs
"""

import argparse
import copy
import json
import os
import subprocess # nosec - B404 (security implications considered)

import iut.config
import iut.error
import iut.run


def parse_args(package_root, toolchain_cfg):
    """ Parse script arguments """
    product_name = toolchain_cfg["product"]["name"]

    p = argparse.ArgumentParser(
        add_help=False,
        description=f"Create the {product_name} post-installation or post-upgrade report")

    iut.config.create_common_argument_group(p, package_root)

    args = p.parse_args()
    args.prog = p.prog

    return args


def update_paths(collector_cfg, toolchain_cfg):
    """ Process the provided collector config to prefix template paths with actual toolchain specific paths """

    cfg = copy.deepcopy(collector_cfg)

    for subdir, rules in cfg.items():
        for idx, spec in enumerate(rules.get("paths", [])):
            parent_var = spec.get("parent", "repo")
            parent_lut = {
                "repo": toolchain_cfg["path"]["full"]["repo"],
                "logs": os.path.join(toolchain_cfg["path"]["full"]["repo"], toolchain_cfg["path"]["part"]["logs"])
            }

            if parent_var not in parent_lut:
                raise iut.error.IutError(
                    iut.error.Codes.CONFIG_ERROR, "IUT-X",
                    f"Unsupported parent directory variable ({parent_var}) in the collector configuration"
                    f" ({subdir}.paths.{idx})\n"
                    f"    Supported variables: {', '.join(parent_lut)}")

            spec["path"] = os.path.join(parent_lut[parent_var], spec["path"])

    return cfg


def main(args, toolchain_cfg): # pylint: disable=unused-argument
    """ Script entry function """

    config_path = os.path.join(toolchain_cfg["path"]["full"]["repo"], toolchain_cfg["path"]["part"]["report_config"])

    with open(config_path) as f:
        conf = json.load(f)

    conf = update_paths(conf, toolchain_cfg)

    collector_cmd_path = os.path.join(
        toolchain_cfg["path"]["full"]["repo"], toolchain_cfg["path"]["part"]["scripts"], "log_collector.py")

    subprocess.run( # nosec - B603 (the user is the system administrator - the input is trusted)
        [collector_cmd_path, "--stdin", "--output-dir", "report_out", "--force"],
        input=json.dumps(conf).encode(), check=True)

    return iut.error.Codes.NO_ERROR


def run_main(toolchain_cfg):
    """ Convenience entry function wrapper to be called from the top-most se_report.py script """
    iut.run.run(main, parse_args, toolchain_cfg)
