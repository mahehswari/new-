# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

""" YAML data utilities """

import logging
import os
import yaml

# pylint: disable=import-error
import seo.error


def indent_error_msg(msg):
    """ Indent the multiline YAML parsing error message taken from the yaml.YAMLError exception.

        The only purpose of this function is to improve the error presentation and make it work better with the error
        details are indented convention.
    """
    joined = "\n    ".join(str(msg).splitlines())
    return f"    {joined}"


def load(file_path):
    """ Read and parse given yaml file """

    logging.debug("Trying to read and parse the yaml file ('%s')", os.path.relpath(file_path))

    try:
        with open(file_path, encoding="utf-8") as input_file:
            return yaml.safe_load(input_file)
    except OSError as e:
        raise seo.error.AppException(
            seo.error.Codes.FILE_OPEN_ERROR,
            f"Failed to load the '{file_path}' YAML file:\n    {e}").inner(str(e)) from e
    except yaml.YAMLError as e:
        raise seo.error.AppException(
            seo.error.Codes.RUNTIME_ERROR,
            f"Failed to parse the '{file_path}' YAML file:\n{indent_error_msg(e)}").inner(str(e)) from e


def save(data, file_path):
    """ Saves the object in data file at given file_path """

    try:
        with open(file_path, "w") as f:
            yaml.dump(data, f, get_dumper(), default_flow_style=False, allow_unicode=True)
    except OSError as e:
        raise seo.error.AppException(seo.error.Codes.RUNTIME_ERROR,
            f"Failed to save the '{os.path.relpath(file_path)}' YAML file:\n    {e}") from e


def get_dumper():
    """ Return a tailored YAML dumper """
    # https://github.com/yaml/pyyaml/issues/234
    class Dumper(yaml.Dumper):  # pylint: disable=too-many-ancestors
        """ Custom dumper to keep proper indentation level """
        def increase_indent(self, flow=False, indentless=False):
            return super().increase_indent(flow=flow, indentless=False)

    # https://stackoverflow.com/questions/37200150/can-i-dump-blank-instead-of-null-in-yaml-pyyaml
    # change a None object representer in custom Dumper class (empty string instead of default 'null')
    def represent_none(dumper, _):
        """ Custom representer for None object """
        return dumper.represent_scalar('tag:yaml.org,2002:null', '')
    yaml.add_representer(type(None), represent_none, Dumper=Dumper)

    # change an empty dict object representer in custom Dumper class (empty string instead of default '{}')
    def represent_dict(dumper, data):
        """ Custom representer for empty dict object """
        if not data:
            return dumper.represent_data(None)
        else:
            return dumper.represent_dict(data.items())
    yaml.add_representer(dict, represent_dict, Dumper=Dumper)

    return Dumper
