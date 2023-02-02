# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Logger configuration utilities

Warning:
    This module is a part of the Standard Library Only (SLO) submodule, and as such, it mustn't directly or indirectly
    import any third-party modules (i.e., modules that aren't part of the Python standard library)
"""

import logging
import sys
import os

import seo.slo.error


def create_console_handler(prog_name, debug_flag):
    """ Create the console logging handler

        Parameters:
            prog_name - program name as provided by the argparse.ArgumentParser.prog field
            debug_flag - if true, the log threshold will be set to DEBUG and the logs will be printed in a verbose
                format; otherwise the log threshold will be set to INFO
    """

    entry_fmt_long = f"%(asctime)s.%(msecs)03d {prog_name}: [%(levelname)s] %(message)s (%(module)s@%(lineno)d)"
    entry_fmt_short = f"{prog_name}: [%(levelname)s] %(message)s"
    date_fmt = "%H:%M:%S"

    handler = logging.StreamHandler(sys.stderr)
    if debug_flag:
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(entry_fmt_long, date_fmt))
    else:
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter(entry_fmt_short, date_fmt))

    return handler


def create_file_handler(prog_name, logs_path):
    """ Create the file logging handler

        Parameters:
            prog_name - program name as provided by the argparse.ArgumentParser.prog field
            logs_path - path to the logs output directory
    """

    entry_fmt = (
        "%(asctime)s.%(msecs)03d [%(levelname)5.5s] %(message)s (%(module)s@%(lineno)d)")
    date_fmt = "%Y-%m-%d_%H:%M:%S"

    prog_base = os.path.splitext(os.path.basename(prog_name))[0]
    file_path = os.path.join(logs_path, f"{prog_base}.log")

    try:
        os.makedirs(logs_path, exist_ok=True)
    except OSError as e:
        raise seo.slo.error.AppException(
            seo.slo.error.Codes.RUNTIME_ERROR,
            f"Failed to create the logs directory ({os.path.relpath(logs_path)}):\n"
            f"    {e}")

    try:
        with open(file_path, "a") as f:
            f.write(f"{'='*119}\n")
    except OSError as e:
        raise seo.slo.error.AppException(
            seo.slo.error.Codes.RUNTIME_ERROR,
            f"Failed to write to the log file ({os.path.relpath(file_path)}):\n"
            f"    {e}")

    handler = logging.FileHandler(file_path)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(entry_fmt, date_fmt))

    logging.info("Program logs are saved to the '%s' file", os.path.relpath(file_path))

    return handler


def config(prog_name, debug_flag, logs_path=None):
    """ Configure the logging package considering provided CLI arguments

        Parameters:
            prog_name - program name as provided by the argparse.ArgumentParser.prog field
            debug_flag - enable more verbose screen logs when true; see the create_console_handler function doc
            logs_path - path to the logs output directory; when None, the file logging will be disabled
    """

    # Enable the console logger in the first place. Splitting it from the file handler creation will allow consistent
    # error handling if a runtime error occurs during the file handler creation:
    logging.getLogger().addHandler(create_console_handler(prog_name, debug_flag))
    logging.getLogger().setLevel(logging.DEBUG)
    # Enable the file logger:
    if logs_path:
        logging.getLogger().addHandler(create_file_handler(prog_name, logs_path))
