# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Hooks for the se_install script
"""

import logging

def init(toolchain_cfg, platform_cfg): # pylint: disable=unused-argument
    """ A hook called as one of the first actions of the se_install script

        Parameters:
            toolchain_cfg - install and upgrade toolchain config as provided to the main function
            platform_cfg - platform configuration data as returned by the iut.config.load_platform_cfg function
    """

    logging.debug("Dummy hooks.install.init hook executed")
