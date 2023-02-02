#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Full provisioning control script wrapper adjusting it to a specific experience kit
"""

import se_config


if __name__ == "__main__":
    CFG = se_config.get_toolchain_cfg()
    se_config.add_import_path(CFG)
    import iut.slo.deps # pylint: disable=import-error, E0611
    iut.slo.deps.check_deps(CFG) # pylint: disable=no-member
    import se_report_cli # pylint: disable=import-error
    se_report_cli.run_main(CFG)
