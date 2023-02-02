# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation

""" Offline installation package metadata handling helpers """

import datetime
import logging
import os
import subprocess # nosec - B404 (security implications considered)
import seo.git
import seo.yaml


def get_path(toolchain_cfg, package_path):
    """ Compose metadata file path relative to an offline installation package path """

    return os.path.join(package_path, toolchain_cfg["path"]["part"]["package"]["metadata"])


def update_file(toolchain_cfg, package_path):
    """ Set the metadata build.end_ts field to indicate that the build process has ended (IUP/A/28)
    """
    metadata_path = get_path(toolchain_cfg, package_path)

    # Load the existing metadata file:
    #     This file is generated and saved by the create_file function. The case of it being missing or malformed will
    #     be considered a bug just like a crash. Because of that, there is no need to catch the seo.error.AppException
    #     error and raise the iut.error.IutError exception instead.
    metadata = seo.yaml.load(metadata_path) # nosec - B506 (project specific wrapper, safe_load used internally)

    metadata.get('build', {})['end_ts'] = datetime.datetime.now() # TODO: Include timezone information

    # Overwrite the existing metadata file:
    #     No need to catch seo.error.AppException here. A failure indicates the application bug rather than the system
    #     operator error.
    seo.yaml.save(metadata, metadata_path)

    logging.info("Metadata file updated successfully")


def create_file(toolchain_cfg, package_path):
    """ Create a new metadata file (IUP/A/27) """

    metadata = {
        'product': {
            'name': toolchain_cfg["product"]["name"],
            'version': toolchain_cfg["product"]["version"]
        },
        'build': {
            'start_ts': datetime.datetime.now() # TODO: Include timezone information
        },
        'repo': {
            'describe': None,
            'commit': None,
            'origin': None
        }
    }

    # Dump details of the package root repository:
    command = ['git', 'rev-parse', 'HEAD']
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, # nosec - B603 (subprocess call)
                          check=False, universal_newlines=True)
    if proc.returncode == 0:
        metadata['repo']['commit'] = proc.stdout.strip()
    else:
        logging.warning("Failed to acquire the repository HEAD commit")

    proc = subprocess.run( # nosec - B603, B607 (subprocess call)
        ['git', 'describe', '--tags'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, universal_newlines=True)
    if proc.returncode == 0:
        metadata['repo']['describe'] = proc.stdout.strip()
    else:
        logging.warning("Failed to acquire the repository HEAD commit")

    command = ['git', 'config', '--get', 'remote.origin.url']
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, # nosec - B603 (subprocess call)
                          check=False, universal_newlines=True)
    if proc.returncode == 0:
        metadata['repo']['origin'] = seo.git.strip_credentials(proc.stdout.strip())
    else:
        logging.warning("Failed to acquire the repository origin url")

    # Save the generated metadata to a new file:
    #     No need to catch seo.error.AppException here. The application is responsible for the directory creation, so a
    #     failure indicates the application bug rather than the system operator error.
    seo.yaml.save(metadata, get_path(toolchain_cfg, package_path))
