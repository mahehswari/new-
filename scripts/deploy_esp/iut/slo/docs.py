# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Troubleshooting documentation related functions

Warning:
    This module is a part of the Standard Library Only (SLO) submodule, and as such, it mustn't directly or indirectly
    import any third-party modules (i.e., modules that aren't part of the Python standard library)
"""

import logging
import os
import re
import urllib


def get_article_doc(toolchain_cfg, article_id):
    """ Determine the troubleshooting document, which is supposed to include the article

        The document is determined based on an ordered list of regular expression patterns mapped to file names. This
        mapping is defined in the toolchain configuration and is only available in the online mode. In the offline
        mode, the articles are stored locally and extracted from the source document, so it is possible to provide the
        URL without knowing from which document it comes.
    """

    for pattern, file_name in toolchain_cfg["docs"]["map"]:
        if re.match(pattern, article_id) is not None:
            return file_name

    logging.debug("No matching troubleshooting document found for the '%s' article", article_id)
    return None


def make_offline_article_url(toolchain_cfg, article_id):
    """ Construct the offline troubleshooting article URL """

    article_path = os.path.join(toolchain_cfg["path"]["part"]["docs"], "article", f"{article_id}.html")

    if not os.path.exists(article_path):
        return None

    url_parts = (
        "file",
        "", # netloc
        os.path.realpath(article_path),
        "", # params
        "", # query
        "") # fragment

    return urllib.parse.urlunparse(url_parts)


def make_online_article_url(toolchain_cfg, article_file, article_id):
    """ Construct the online troubleshooting article URL """
    base_url_parts = urllib.parse.urlparse(toolchain_cfg["docs"]["url"])

    url_parts = (
        base_url_parts.scheme,
        base_url_parts.netloc,
        os.path.join(
            base_url_parts.path, "blob", toolchain_cfg["docs"]["branch"],
            toolchain_cfg["docs"]["path"], article_file), # path
        "", # params
        "", # query
        article_id) # fragment

    return urllib.parse.urlunparse(url_parts)
