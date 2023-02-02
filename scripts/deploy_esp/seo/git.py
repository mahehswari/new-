# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021 Intel Corporation

""" Git utilities """

import urllib
import subprocess  # nosec - B603, B404
import logging

# pylint: disable=import-error
import seo.error

def clone(url, path, username=None, password=None, git_options=None):
    """Does git clone from url to path with supplied git_options,
    user and password have to be specified but can be empty or None"""

    log_url = apply_credentials(url, "***" if username else None, "***" if password else None)
    if username or password:
        url = apply_credentials(url, username, password)

    cmd = ["git", "clone", url, path]

    if git_options:
        cmd += git_options

    log_cmd = cmd[:]
    log_cmd[2] = log_url
    logging.debug("Executing command: %s", " ".join(map(str, log_cmd)))

    try:
        subprocess.run(cmd, check=True) # nosec - B603
    except subprocess.CalledProcessError as e:
        raise seo.error.AppException(seo.error.Codes.RUNTIME_ERROR,
            f"Failed to clone the repository from {log_url} to {path}") from e


def apply_credentials(url, username, password):
    """Return the provided url with the user:password part replaced with the given username and password"""

    p = urllib.parse.urlparse(url)

    netloc = p.netloc.split('@')[-1]

    if username and password:
        c = f"{username}:{password}"
    else:
        c = f"{username or ''}{password or ''}"

    if c:
        p = p._replace(netloc=f"{c}@{netloc}")
    else:
        p = p._replace(netloc=netloc)

    return p.geturl()


def strip_credentials(url):
    """ Return the provided url with the user:password part stripped (if set) """
    return apply_credentials(url, None, None)


def checkout(ref_or_sha, cwd):
    """Does a git checkout ref_or_sha using cwd as cwd"""

    cmd = [ "git", "checkout", ref_or_sha]

    logging.debug("Invoking git checkout %s in %s", ref_or_sha, cwd)

    try:
        subprocess.run(cmd, check=True, cwd=cwd) # nosec - B603
    except subprocess.CalledProcessError as e:
        raise seo.error.AppException(seo.error.Codes.RUNTIME_ERROR,
            f"Failed to git checkout {ref_or_sha} in {cwd}") from e
