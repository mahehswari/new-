# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Various system helpers

Warning:
    This module is a part of the Standard Library Only (SLO) submodule, and as such, it mustn't directly or indirectly
    import any third-party modules (i.e., modules that aren't part of the Python standard library)
"""

import copy
import re


_ASSIGNMENT_REGEXP = r"=.+?(\s+|$)"
_CLEAR = ["--git-password"]
_REPLACEMENT = "<provided>"


def clear_password(args, *, clear=None, replacement=_REPLACEMENT):
    """ Return a copy of the command line arguments with confidential data replaced

        Parameters:
            args - command line list
            clear - list of options to clear
            replacement - the value to be used as a replacement for cleared values
    """

    args = copy.copy(args)
    if clear is None:
        clear = _CLEAR

    for i, a in enumerate(args):
        for c in clear:
            if a == c and len(args) >= i + 1:
                args[i + 1] = replacement
            elif re.search(c + _ASSIGNMENT_REGEXP, a):
                args[i] = re.sub(c + _ASSIGNMENT_REGEXP, c + "=" + replacement, a)

    return args
