#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation

"""
SE Install and Upgrade Toolchain: Create package checksums file
"""

import logging
import os
import subprocess # nosec - B404 (security implications considered)

import iut.error


def verify_checksum_files(toolchain_cfg):
    """ Verify package checksums (IUP/A/47) """

    checksum_files = (toolchain_cfg["path"]["part"]["package"]["checksum"]["datafiles"],
                      toolchain_cfg["path"]["part"]["package"]["checksum"]["metafiles"])

    for checksum_file in checksum_files:
        cmd = ["sha256sum", "--check", "--quiet", checksum_file]

        try:
            subprocess.run(cmd, # nosec - B603 (subprocess call)
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=True,
                        encoding = "utf-8"
                        )
        except subprocess.CalledProcessError as e:
            raise iut.error.IutError(
                iut.error.Codes.INTERNAL_ERROR,
                "IUT-X",
                f"Checksum verification for file {checksum_file} failed:\n    {e.stderr}{e.stdout}") from e

        logging.info("Checksum file %s verified successfully", checksum_file)


def create_package_checksum_file(toolchain_cfg, package_root):
    """ Calculate the checksums for all output package files (IUP/A/45) """

    metadata = toolchain_cfg["path"]["part"]["package"]["metadata"]
    checksum_file_name = toolchain_cfg["path"]["part"]["package"]["checksum"]["datafiles"]

    cmd = [
        "find", ".", "-type", "f", "-not", "-name", metadata, "-a", "-not", "-name", checksum_file_name,
        "-exec", "sha256sum", "{}", "+"]

    with open(os.path.join(package_root, checksum_file_name), 'wb') as f:
        try:
            subprocess.run(cmd, stdout=f, cwd=package_root, check=True) # nosec - B603 (subprocess call)
        except subprocess.CalledProcessError as e:
            raise iut.error.IutError(
                iut.error.Codes.INTERNAL_ERROR,
                "IUT-X",
                f"Failed to generate package checksum file:\n    {e}") from e

        logging.info("Package checksum file created successfully")


def create_metadata_checksum_file(toolchain_cfg, package_root):
    """ Calculate the checksums for metadata (IUP/A/46) """

    metadata = toolchain_cfg["path"]["part"]["package"]["metadata"]
    checksum_file_name = toolchain_cfg["path"]["part"]["package"]["checksum"]["metafiles"]

    cmd = ["sha256sum", metadata]

    with open(os.path.join(package_root, checksum_file_name), 'wb') as f:
        try:
            subprocess.run(cmd, stdout=f, cwd=package_root, check=True) # nosec - B603 (subprocess call)
        except subprocess.CalledProcessError as e:
            raise iut.error.IutError(
                iut.error.Codes.INTERNAL_ERROR,
                "IUT-X",
                f"Failed to generate metadata checksum file:\n    {e}") from e

        logging.info("Metadata checksum file created successfully")
