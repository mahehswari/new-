# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
SLO: Standard Library Only

This module provides utilities relying on the standard library only. They are used for actions that must be performed
before it can be confirmed that all the python prerequisites are installed. The primary uses are:

* Implementation of the se_env.py command, which is supposed to install the prerequisites (so it can't fail if some
  python modules are missing)
* Python dependencies check performed in remaining se_*.py commands
"""
