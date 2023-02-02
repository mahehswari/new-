# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation

""" Directory info/creation/removal with business logic utilites """

import pathlib
import subprocess # nosec - B404 (security implications considered)
import os
import logging
import shutil
from typing import Set

import seo.error
import iut.config
import iut.error
import iut.metadata

def get_tracked_dirs_files(git_path: os.PathLike) -> Set[pathlib.Path]:
    """Gets set of git tracked files and directiories.
    Args:
        git_path: Path inside git directory relative to which
            dirs and files are searched.
    Returns:
        set: Files and directories that are tracked by git tool
            relative to git_path with depth 1.
    """

    command = ["git", "-C", str(git_path), "ls-files"]
    try:
        out = subprocess.run(command, # nosec - B603 (subprocess call)
                             stdout=subprocess.PIPE,
                             text=True,
                             check=True)
    except subprocess.CalledProcessError as e:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR,
            "IUT-X",
            "Failed to collect Intel Smart Edge git repository details") from e

    all_files = set(out.stdout.splitlines())
    root_dirs = set()
    root_files = set()
    for file in all_files:
        path = pathlib.Path(file)
        parents = list(path.parents)
        if len(parents) > 1:
            root_dirs.add(parents[-2])
        else:
            root_files.add(path.resolve())
    return root_dirs.union(root_files)


def create_output_path(toolchain_cfg: dict, out_path: os.PathLike, force=False):
    """Creates output path after git/subdirectories business logic validation.

        Params:
            toolchain_cfg: the toolchain configuration as provided to the main function
            out_path: output directory path
    """
    repo_root = pathlib.Path(toolchain_cfg["path"]["full"]["repo"]).resolve()
    out_path = pathlib.Path(out_path).resolve()
    if not repo_root.joinpath(".git").exists():
        raise iut.error.IutError(
            iut.error.Codes.ARGUMENT_ERROR,
            "IUT-X",
            f"Failed to find .git directory in given path: ({repo_root}).")
    disallowed = [p.resolve() for p in get_tracked_dirs_files(repo_root)]
    disallowed.append(pathlib.Path(".git").resolve())

    if pathlib.Path(os.path.commonprefix((out_path, repo_root,))) == out_path:
        raise iut.error.IutError(
            iut.error.Codes.ARGUMENT_ERROR,
            "IUT-X",
            f"The path ({out_path}) can not be parent path for "
            f"root path ({repo_root}).")
    for path in disallowed:
        common = pathlib.Path(os.path.commonprefix((out_path, path,)))
        if common == path:
            raise iut.error.IutError(
                iut.error.Codes.ARGUMENT_ERROR,
                "IUT-X",
                f"The path {out_path} is either tracked or used by "
                "source git repository "
                "please provide different output path.")

    if out_path.exists():
        logging.debug("The output directory ('%s') already exists", os.path.relpath(out_path))

        current_name = toolchain_cfg["product"]["name"]
        current_version = toolchain_cfg["product"]["version"]

        metadata_path = pathlib.Path(iut.metadata.get_path(toolchain_cfg, out_path))

        if metadata_path.exists():
            metadata = seo.yaml.load(metadata_path) # nosec - B506 (project specific wrapper, safe_load used internally)
            out_name = metadata["product"]["name"]
            out_version = metadata["product"]["version"]
            logging.debug("Found the metadata file ('%s')", os.path.relpath(metadata_path))
            logging.debug(
                "The output directory ('%s') contains the following installation package: \n"
                "    product: %s\n"
                "    version: %s",
                os.path.relpath(out_path), out_name, out_version)

            if current_name != out_name or current_version != out_version:
                logging.warning(
                    "The output directory ('%s') contains the following installation package, and it's is different"
                    " than the one the command will build:\n"
                    "    Installation package found in the output directory:\n"
                    "        product: %s\n"
                    "        version: %s\n"
                    "    Installation package to be built:\n"
                    "        product: %s\n"
                    "        version: %s",
                    os.path.relpath(out_path), out_name, out_version, current_name, current_version)

        if not force:
            raise iut.error.IutError(
                iut.error.Codes.ARGUMENT_ERROR,
                "IUT-4",
                f"The output directory ('{os.path.relpath(out_path)}') already exists\n"
                f"    Choose a different directory, remove it manually or use the {iut.config.FORCE_OPT} option to"
                " remove it automatically")

        logging.info(
            "Removing the existing output directory ('%s') as the %s option was specified",
            os.path.relpath(out_path), iut.config.FORCE_OPT)

        try:
            shutil.rmtree(out_path)
        except OSError as os_exception:
            logging.error(
                "Failed to remove file: %s %s.",
                os_exception.filename, os_exception.strerror)
            raise iut.error.IutError(
                iut.error.Codes.RUNTIME_ERROR,
                "IUT-X",
                f"Failed to remove the output directory ({os.path.relpath(out_path)}):\n"
                f"    {os_exception}\n\n"
                f"    Please, remove the output directory manually and run the {toolchain_cfg['prog']} command again"
            ) from os_exception
    try:
        os.mkdir(out_path, mode=0o755)
    except FileNotFoundError as e:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR,
            "IUT-X",
            f"Parent directory does not exist: {e} \n"
            "Please create all intermediate directories.")

    logging.info("Successfully created the output directory ('%s')", os.path.relpath(out_path))
