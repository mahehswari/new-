# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Error handling utilities

Warning:
    This module is a part of the Standard Library Only (SLO) submodule, and as such, it mustn't directly or indirectly
    import any third-party modules (i.e., modules that aren't part of the Python standard library)
"""

import seo.slo.error

Codes = seo.slo.error.Codes

class IutError(seo.slo.error.AppException):
    """
    This exception indicates Install and Upgrade Toolchain error.

    If not handled, it will result in the application termination with the error message and article reference printed
    on the screen. Toolchain applications will present this message to the toolchain user (SE Platform operator), so it
    should be of high quality (both in terms of language correctness, helpfulness, and unambiguousness.
    """
    def __init__(self, code, article_id, msg):
        super().__init__(code, msg)
        self.article_id = article_id
