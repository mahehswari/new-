# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

""" SE Install and Upgrade Toolchain script execution utilities. """

import json
import os

import seo.config
import seo.error
import iut.error
import iut.slo.run


def validate_toolchain_cfg(toolchain_cfg):
    """ Validate toolchain configuration correctness

        The toolchain configuration is not user-provided. It is validated to detect developer errors early and
        unconditionally. It is acceptable if some crashes related to invalid toolchain config occur before the
        validation could be performed (e.g. in the `iut.slo.config.augment_toolchain_cfg` or `seo.slo.logger.config`
        functions) because the objective is still achieved (a developer error is detected).
    """

    toolchain_schema_path = os.path.join(
        toolchain_cfg["path"]["full"]["repo"],
        toolchain_cfg["path"]["part"]["data"],
        "schema",
        "toolchain_cfg.json")
    try:
        with open(toolchain_schema_path, 'r', encoding="utf-8") as f:
            toolchain_schema = json.load(f)
    except OSError as e:
        raise iut.error.IutError(
            iut.error.Codes.FILE_OPEN_ERROR,
            "IUT-X",
            f"Failed to open the file ({os.path.relpath(toolchain_schema_path)}):\n"
            f"    {e}")

    try:
        seo.config.validate(
            toolchain_cfg, toolchain_schema_path,
            toolchain_schema, "Toolchain configuration")
    except seo.error.AppException as e:
        raise iut.error.IutError(
            iut.error.Codes.CONFIG_ERROR,
            "IUT-X",
            e.msg)


def run(main_cb, parse_args_cb, toolchain_cfg):
    """ Wrapper executing provided IUT application entry function

        This function depends indirectly on third-party modules and, as such, can't be used by the commands that can't
        verify it in the top-level wrapper scripts (e.g., the se_env.py script).
    """

    def wrapped_main_cb(cli_args, toolchain_cfg):
        # TODO: Validation in the offline mode is disabled temporarily and it will be provided in the scope of
        #       ESS-16834
        if not toolchain_cfg['context']['offline_flag']:
            validate_toolchain_cfg(toolchain_cfg)

        return main_cb(cli_args, toolchain_cfg)

    iut.slo.run.run(wrapped_main_cb, parse_args_cb, toolchain_cfg)
