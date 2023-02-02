# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Utility command used to generate the Smart Edge platform configuration file and provide some convenience
functionalities related to the configuration file.
"""

import argparse
import logging
import os

import iut.error
import iut.run
import iut.slo.config


_PRINT_OPT = "--print"
_OUTPUT_OPT = "--output"


def parse_args(package_root, toolchain_cfg):
    """ Parse script arguments """
    product_name = toolchain_cfg["product"]["name"]

    p = argparse.ArgumentParser(
        add_help=False,
        description=f"""
            Generate a new {product_name} configuration file according to the options provided
        """)

    g = p.add_argument_group("common arguments")
    iut.slo.config.add_debug_argument(g)
    iut.slo.config.add_help_argument(g)

    g = p.add_argument_group("output arguments")

    default_config_path = os.path.relpath(os.path.join(package_root, "se.yaml"))

    g.add_argument(
        "-p", _PRINT_OPT, action="store_true", dest="print_config",
        help="""
            display the generated configuration on the console
            """)

    g.add_argument(
        "-o", _OUTPUT_OPT, action="store", dest="output_path", nargs='?', const=default_config_path, metavar="PATH",
        help="""
            PATH to the output file into which the script will write the generated configuration
            (default: %(const)s)
            """)


    args = p.parse_args()
    args.prog = p.prog
    return args


def save_config(args, toolchain_cfg):
    """Write the config to file"""
    if os.path.exists(args.output_path):
        raise iut.error.IutError(
            iut.error.Codes.ARGUMENT_ERROR,
            "IUT-X",
            f"The '{os.path.relpath(args.output_path)}' file already exists:\n"
            f"    Please choose a different file name or remove it and execute the {args.prog} command again.")

    try:
        with open(args.output_path, "w") as f:
            f.write(toolchain_cfg["configs"]["default"])
            logging.info("Created the '%s' platform configuration file", os.path.relpath(args.output_path))
    except OSError as e:
        raise iut.error.IutError(
            iut.error.Codes.FILE_OPEN_ERROR,
            "IUT-X",
            f"Failed to create the '{os.path.relpath(args.output_path)}' file:\n"
            f"    {e}") from e


def main(args, toolchain_cfg): # pylint: disable=unused-argument
    """ Script entry function """

    if not args.print_config and args.output_path is None:
        logging.warning(
            "The command had no effect\n"
            "    To generate platform configuration, use '%s' or '%s' or both of these options",
            _PRINT_OPT, _OUTPUT_OPT)

    if args.print_config:
        print(toolchain_cfg["configs"]["default"])

    if args.output_path is not None:
        save_config(args, toolchain_cfg)

    return iut.error.Codes.NO_ERROR


def run_main(toolchain_cfg):
    """ Convenience entry function wrapper to be called from the top-most se_config.py script """
    iut.run.run(main, parse_args, toolchain_cfg)
