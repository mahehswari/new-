#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Wrapper for the Smart Edge Provisioning Host environment initialization and verification utility
"""

import se_config


if __name__ == "__main__":
    CFG = se_config.get_toolchain_cfg()
    se_config.add_import_path(CFG)
    # This script intentionally skips the dependencies check as one of its purposes is to install them
    import se_env_cli # pylint: disable=import-error
    se_env_cli.run_main(CFG)
