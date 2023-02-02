# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

""" Various sequence helpers """

def chop(seq, chunk_size):
    """ Split the provided sequence into a list of chunks of given size. The last chunk may be shorter than others if
        there isn't enough items in the sequence
    """
    if seq:
        return [seq[i:i+chunk_size] for i in range(0, len(seq), chunk_size)]
    else:
        return []
