# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation

"""Provides experience-kit copying utilites"""

import argparse
import logging
import os
import shutil
import subprocess # nosec - B404
from typing import Optional

import seo.git

import iut.error


def copy_experience_kits(platform_cfg: dict, cli_args: argparse.Namespace) -> Optional[str]:
    """Copies or clones experience kits defined in platform config into output directory.

    The function will copy only experience kits that are actually added as 'experience_kit' for some cluster.
    If some ek is definied in 'experience_kits' config, but not in any cluster warning will be
    showed and it will be ignored.

    Args:
        platform_cfg: platform config dictionary with information about eks and clusters.
        cli_args: command line arguments with information about output path and git credentials

    Returns:
        string: absolute path for new toolchain ek
    """
    output_path = os.path.abspath(cli_args.output_path)
    outdir = os.path.join(output_path, "experience-kits")
    try:
        os.mkdir(outdir, mode=0o755)
    except OSError as e:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR,
            "IUT-X",
            f"Failed to create experience-kits directory '{outdir}':\n{e}") from e

    logging.info("Output directory for ek's is '%s'", outdir)

    experience_kits = platform_cfg["experience_kits"]
    deployed_kits = set((cluster["experience_kit"]["name"] for cluster in platform_cfg["clusters"]))
    toolchain_path = None
    for ek in experience_kits:
        ek_name = ek["name"]
        if ek_name not in deployed_kits:
            logging.warning("The kit '%s' is not added to any cluster config.", ek["name"])
            continue
        dstpath = os.path.join(outdir, ek_name)
        # Currently the new toolchain will be the first ek
        # To be discussed if some flag in cfg should point that
        if not toolchain_path:
            toolchain_path = dstpath

        if "path" in ek:
            ekpath = os.path.abspath(ek["path"])
            check_for_git_changes(repopath=ekpath, reponame=ek_name)
            logging.info(
                "Copying the '%s' experience kit from '%s' to '%s'",
                ek_name, os.path.relpath(ekpath), os.path.relpath(dstpath))
            try:
                shutil.copytree(ekpath, dstpath,
                                ignore=get_copy_filter(ekpath, output_path),
                                symlinks=True,
                                copy_function=shutil.copy)
            except shutil.Error as e:
                errors = "\n\t\t".join([err[2] for err in e.args[0]])
                raise iut.error.IutError(
                    iut.error.Codes.RUNTIME_ERROR,
                    "IUT-X",
                    f"Failed to copy '{ekpath}' to '{dstpath}'.\nErrors:\n\t\t{errors}"
                    ) from e
        else:
            ek_url = ek["url"]
            logging.info("Cloning ek '%s' from '%s' to '%s'", ek_name, ek_url, dstpath)
            seo.git.clone(ek_url, dstpath, username=cli_args.git_user, password=cli_args.git_password)

    return toolchain_path

def check_for_git_changes(repopath: str, reponame: str=None):
    "Notifies about modified files in given git repo path."
    diffcmd = subprocess.run(["git", "-C", repopath, "ls-files", "-m"], # nosec - B603, B607 (subprocess call)
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=False)
    if diffcmd.returncode != 0:
        logging.error("Failed to list modified files for '%s' : '%s'\n"
            "Failed cmd: '%s'\n"
            "\t\tStdout: %s\n"
            "\t\tStderr: %s",
            reponame, repopath, subprocess.list2cmdline(diffcmd.args), diffcmd.stdout, diffcmd.stderr)
        return
    changed_files = set(diffcmd.stdout.splitlines())
    if changed_files:
        logging.warning("Repo '%s' has following files modified:\n\t\t%s",
            reponame or repopath,
            "\n\t\t".join(changed_files))

def get_copy_filter(ekpath: str, output_path: str):
    """Returns filter for shutil.copytree ignore when copying experience-kit.

    The filter will include .iutignore files if it exists in ekpath.
    """
    iutignore = os.path.join(ekpath, ".iutignore")

    ignored = [output_path]
    if os.path.exists(iutignore):
        try:
            lscmd = subprocess.run( # nosec - B603, B607 (subprocess.run call)
                ["git", "-C", ekpath, "ls-files", "-X", iutignore, "-cmoki"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                check=True)
        except subprocess.CalledProcessError as e:
            msg = f"Failed to get list of ignored files for '{ekpath}'.\n" \
                  f"Failed cmd: '{subprocess.list2cmdline(e.cmd)}'\n" \
                  f"\t\tStdout: {e.stdout}\n" \
                  f"\t\tStderr: {e.stderr}"
            raise iut.error.IutError(
                iut.error.Codes.RUNTIME_ERROR,
                "IUT-X",
                msg) from e

        ignored.extend(lscmd.stdout.splitlines())
    def _ignore(path, names):
        to_ignore = []
        for i in ignored:
            if not os.path.isabs(i):
                i = os.path.abspath(os.path.join(ekpath, i))
            to_ignore.extend([f for f in names if os.path.abspath(os.path.join(path, f)) == i])
        return set(to_ignore)
    return _ignore
