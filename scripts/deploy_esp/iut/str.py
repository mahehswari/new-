# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

""" Various string helpers """

def sgpl(val, singular="", plural="s"):
    """ Plural/singular string variant shortcut function

        Return singular if the value is a sequence of length one or is equal to one after conversion to int. Works for
        types implementing the len method, numbers, and boolean.
    """

    try:
        num = len(val)
    except ValueError:
        num = int(val) # Will work with boolean value, too
    return singular if num == 1 else plural
