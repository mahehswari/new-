# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation

""" Troubleshooting documentation related functions """

import logging
import os
import subprocess  # nosec - B404 (security implications considered)

import seo.git
import iut.error


def build_offline_docs(args, toolchain_cfg, output_root, tmp_root):
    """ Execute the offline documentation build action (IUP/A/10) """

    docs_cfg = toolchain_cfg["docs"]
    url = docs_cfg.get("url")

    if url is not None:
        logging.debug("The offline documentation will be generated from a clone of the following repository: %s", url)
        repo_path = os.path.join(tmp_root, "docs")

        opts = ["--depth=1"]

        branch = docs_cfg.get("branch")
        if branch is not None:
            opts += ["--branch", branch]
            logging.debug("Git will checkout the following branch: %s", branch)
        else:
            logging.debug("Git will checkout the default branch")

        git_user = args.git_user if not None else None
        git_password = args.git_password if not None else None

        seo.git.clone(url, repo_path, git_user, git_password, git_options=opts)
        source_path = os.path.join(repo_path, docs_cfg["path"])
    else:
        source_path = os.path.join(toolchain_cfg["path"]["full"]["repo"], docs_cfg["path"])

    logging.debug("The offline documentation will be generated from the following subdirectory: %s", source_path)

    generate_docs_path = os.path.join(toolchain_cfg["path"]["full"]["toolchain"], "generate_docs.py")
    docs_path = os.path.join(output_root, toolchain_cfg["path"]["part"]["package"]["docs"])

    generate_docs_cmd = [
        generate_docs_path,
        "-o", docs_path,
        source_path]

    # Instruct the generate docs tool to ignore non-critical issues when the se_build script is not in the diagnostic
    #  mode. Otherwise propagate the debug flag to it.
    generate_docs_cmd += ["--debug" if args.debug else "--force"]

    try:
        subprocess.run(generate_docs_cmd, check=True) # nosec - B603 (the user is the system administrator)
    except subprocess.CalledProcessError as e:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR,
            "IUT-X",
            "Failed to generate offline documentation package") from e

    logging.info("Successfully generated the offline documentation package")
