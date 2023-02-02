# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation
# pylint: disable=bad-option-value,useless-option-value # (no-self-use was removed in pylint 2.14)
# pylint: disable=no-self-use # (pytest stylistic convention)
"""Tests to verify the correctness of the jsonschema at config_schema.json"""

from pathlib import Path
from typing import Iterator
import json
import jsonschema
import pytest

class TestConfig:
    """For testing json config"""

    @pytest.fixture
    def mock_validator(self) -> Iterator[jsonschema.Draft7Validator]:
        """ Prepare a jsonschema validator based on data from config_schema.json """
        with open(Path(__file__).parent / "config_schema.json", encoding="utf-8") as schema_file:
            schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "hostname": { "$ref": "#/$defs/hostname" }},
                "required": [ "hostname" ],
                "$defs": json.load(schema_file)["$defs"] }
            print(schema)
        yield jsonschema.Draft7Validator(schema, format_checker=jsonschema.draft7_format_checker)


    def test_valid_hostnames(self, mock_validator):
        "Test if set of hostnames is valid"
        valid = (
            "sub.domain.example",
            "sub-domain.example",
            "sub.domain-example",
            "sub-domain-example",
            "mobica.pl",
            "hostname",
            "host.name",
            "host-name",
            "host--name",
            "01.org",
            "h0st",
            "host1",
            "snilv-02ms.com",
            "snilv---test",
            "master",
            "bazyli.snilp-03.ue-pl",
            "aa")
        for hostname in valid:
            payload = {"hostname": hostname}
            assert mock_validator.is_valid(payload), f"Hostname '{hostname}' should be checked as valid hostname"


    def test_invalid_hostnames(self, mock_validator):
        "Test if set of hostnames is invalid"
        invalid = (
            "Test",
            "TEST.com",
            ".domain.com",
            "domain.com.",
            "unamE",
            "-host.snilp",
            "Host1",
            "host..name",
            "hostname-",
            "hostname.",
            "test-.com",
            "-hostname",
            ".hostname",
            "a",
            "a" * 61 + ".pl")
        for hostname in invalid:
            payload = {"hostname": hostname}
            assert not mock_validator.is_valid(payload), f"Hostname '{hostname}' should be checked as invalid hostname"
