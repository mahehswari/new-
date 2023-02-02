# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Script execution utilities

Warning:
    This module is a part of the Standard Library Only (SLO) submodule, and as such, it mustn't directly or indirectly
    import any third-party modules (i.e., modules that aren't part of the Python standard library)
"""

import logging
import json
import subprocess # nosec - B404 (security implications considered)
import copy
import traceback
import sys

import seo.slo.error
import seo.slo.logger
import iut.slo.config
import iut.slo.docs
import iut.slo.error
import iut.slo.system


def format_iut_error_msg(toolchain_cfg, article_id, msg):
    """ Format troubleshooting error message

        The function extends the message with a link to the related troubleshooting article. It provides a different
        type of link, depending on the environment (offline or online).

        The error message won't provide the link when:
        * The local file system article file doesn't exist.
        * The markdown document which includes the article can't be determined.
        * The troubleshooting documentation source is defined as a local directory.
    """

    if toolchain_cfg["context"]["offline_flag"]:
        browser = "lynx " # A subtle suggestion that no graphical browser is needed to view the documentation
        msg_path = iut.slo.docs.make_offline_article_url(toolchain_cfg, article_id)
    else:
        browser = "" # It would be cumbersome to authenticate using lynx in the closed GitHub projects, so let's not
                     #  suggest it.
        article_file = iut.slo.docs.get_article_doc(toolchain_cfg, article_id)

        if article_file is None:
            # The article id couldn't be mapped to the source markdown document
            msg_path = None
        elif "url" in toolchain_cfg["docs"]:
            msg_path = iut.slo.docs.make_online_article_url(toolchain_cfg, article_file, article_id)
        else:
            # The troubleshooting article link won't be provided for the local provisioning documentation source as the
            #  markdown documents can't be directly rendered by web browsers and the anchor references don't work with
            #  them. To make this work, the troubleshooting documents would have to be converted to html format and
            #  adding the support for this is considered low priority right now (as the local docs source feature is
            #  not currently proven to be needed).
            msg_path = None

    if msg_path is None:
        # An URL linking to an existing and browser renderable troubleshooting article couldn't be determined.
        #  Provide a generic article reference.
        return (
            f"{msg}\n\n"
            f"    For details, see the following troubleshooting article: {article_id}")

    return (
        f"{msg}\n\n"
        "    For details, see the following troubleshooting article:\n"
        f"        {browser}{msg_path}")


def log_env(toolchain_cfg, cli_args):
    """ Log all the relevant runtime environment information to make it available for production issue diagnostics

        Parameters:
            toolchain_cfg - install and upgrade toolchain config as provided to the main function
            cli_args - parsed command line arguments object as returned by the parse_args function
    """
    logging.debug("The command executed:\n%s", subprocess.list2cmdline(iut.slo.system.clear_password(sys.argv)))

    args = copy.copy(cli_args.__dict__)
    if "git_password" in args and args["git_password"] is not None:
        args["git_password"] = "<provided>" # nosec - B105 (replacement text for real passwords)

    logging.debug("The parsed arguments:\n%s", json.dumps(args, sort_keys=True, indent=4, ensure_ascii=False))
    logging.debug("The toolchain config:\n%s", json.dumps(toolchain_cfg, sort_keys=True, indent=4, ensure_ascii=False))


def run(main_cb, parse_args_cb, toolchain_cfg):
    """ Wrapper executing provided IUT application entry function
    """

    toolchain_cfg = iut.slo.config.augment_toolchain_cfg(toolchain_cfg)
    package_root = toolchain_cfg["path"]["full"]["repo"]
    cli_args = parse_args_cb(package_root, toolchain_cfg)
    toolchain_cfg["prog"] = cli_args.prog

    try:
        seo.slo.logger.config(cli_args.prog, cli_args.debug, toolchain_cfg["path"]["full"]["logs"])
        log_env(toolchain_cfg, cli_args)
        sys.exit(main_cb(cli_args, toolchain_cfg).value)
    except iut.slo.error.IutError as e:
        if cli_args.debug:
            traceback.print_exc(file=sys.stderr)
        logging.error(format_iut_error_msg(toolchain_cfg, e.article_id, e.msg))
        sys.exit(e.code.value)
    except seo.slo.error.AppException as e:
        if cli_args.debug:
            traceback.print_exc(file=sys.stderr)
        logging.error(e.code if e.msg is None else e.msg)
        sys.exit(e.code.value)
