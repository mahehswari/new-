# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

""" Provisioning configuration handling related utilities. """

import json
import logging
import os.path

import jsonschema

# pylint: disable=import-error
import seo.error
import seo.yaml


def validate(config, config_path, schema, file_desc="YAML"):
    """ Validate of configuration data using the provided schema

        The config_path and file_desc parameters serve the error message composition purposes only
    """
    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.draft7_format_checker)

    if validator.is_valid(config):
        logging.debug("The %s file ('%s') validation succeeded", file_desc, config_path)
        return

    msg = [f"The {file_desc} file ('{config_path}') validation failed:"]

    for error in validator.iter_errors(config):
        node = '/'.join([str(p) for p in error.path])
        msg += [
            f"    {node}:",
            f"        {error.message}"]

    raise seo.error.AppException(seo.error.Codes.CONFIG_ERROR, "\n".join(msg))


def load_provisioning_cfg(config_path, root_path):
    """ Load and validate specified provisioning configuration file

        Params:
            config_path - path to the configuration file to be handled
            root_path - path to the shared provisioning script root directory (the one containing the 'deploy_esp.py'
                script and the 'seo' python module)
    """

    cfg = seo.yaml.load(config_path) # nosec - B506 (project specific wrapper, safe_load used internally)
    schema_path = os.path.join(root_path, "config_schema.json")
    with open(schema_path, encoding="utf-8") as schema_file:
        schema = json.load(schema_file)

    # Fundamental schema validation:
    validate(cfg, config_path, schema)

    # Extended validation:
    verify_esp_path_length(cfg["esp"]["dest_dir"])

    logging.debug("The provisioning configuration file ('%s') is valid", config_path)
    return cfg


def verify_esp_path_length(dest_path):
    """The ESP repository destination directory path mustn't be too long to not hit the unix socket path limit within
       the ESP code.

       See: ESS-3861 and https://man7.org/linux/man-pages/man7/unix.7.html
    """

    expected_socket_path = os.path.join(
        os.path.realpath(os.path.abspath(dest_path)),
        "data/tmp/build/docker.sock")

    # How the limit was calculated:
    # For a path of length 107 following error could be seen in the builder.log:
    #     Cannot connect to the Docker daemon at unix:////[...]/docker.sock. Is the docker daemon running?
    # For a path of length greater than 107 following error could be seen in the builder.log:
    #     Unix socket path "//[...]/docker.sock" is too long

    diff = len(expected_socket_path) - 106

    if diff > 0:
        diff_str = "1 character" if diff == 1 else f"{diff} characters"

        raise seo.error.AppException(
            seo.error.Codes.CONFIG_ERROR,
            "The ESP destination directory path is too long.\n"
            f"    Please make the following path shorter by at least {diff_str} to be able to proceed:\n"
            f"    {expected_socket_path}\n\n"
            f"    {seo.error.TS_REF}")
