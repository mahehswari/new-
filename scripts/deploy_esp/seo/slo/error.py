# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Error handling utilities

Warning:
    This module is a part of the Standard Library Only (SLO) submodule, and as such, it mustn't directly or indirectly
    import any third-party modules (i.e., modules that aren't part of the Python standard library)
"""

import enum


TS_REF = "See the Troubleshooting section of the Intel® Smart Edge Open Provisioning Process document"


class Codes(enum.Enum):
    """ Script exit codes """
    NO_ERROR = 0
    GENERIC_ERROR = 1
    MISSING_PREREQUISITE = 2
    ARGUMENT_ERROR = 3
    CONFIG_ERROR = 4
    RUNTIME_ERROR = 5
    INTERNAL_ERROR = 6
    FILE_OPEN_ERROR = 7


class AppException(Exception):
    """
    Exception indicating application error which, if not handled, should result in the
    application exit with the error message printed to the screen
    """
    def __init__(self, code, msg=None):
        super().__init__()
        self.code = code
        self.msg = msg
        self.inner_msg = ""

    def inner(self, msg):
        """ Preserve the inner (wrapped) exception message to be able to repackage the AppException and still include
            the original exception's details. The practical use of this feature is when we want to make a generic
            message provided to AppException more contextual.

            See the seo.yaml.load and iut.config.load_platform_cfg functions for the intended way of use
        """
        self.inner_msg = msg
        return self
