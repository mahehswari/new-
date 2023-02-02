# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation
# pylint: disable=bad-option-value,useless-option-value # (no-self-use was removed in pylint 2.14)
# pylint: disable=no-self-use # (pytest stylistic convention)

""" Test for provisioning configuration handling related utilities. """


import os
from typing import Iterator
import pytest
import conftest
import seo.config


class TestVerifyEspPathLength:
    """Test case for seo.config.verify_esp_path_length"""


    MAX_PATH_LENGTH = 106


    @pytest.fixture(params=(1, 2, 3))
    def dest_path_length(self, request, tmp_path) -> Iterator[int]:
        """ Create temporary directories with filenames of varying length, then compute the maximum allowable path
            length and return it """
        random_path = tmp_path / conftest.random_identifier(length=request.param)
        random_path.mkdir()
        os.chdir(random_path)
        full_docker_path = random_path / "data/tmp/build/docker.sock"
        print(full_docker_path, len(str(full_docker_path)))
        yield TestVerifyEspPathLength.MAX_PATH_LENGTH - len("/") - len(str(full_docker_path))


    def test_path_length(self, dest_path_length):
        "Test if expected socket paths are correctly reported as having valid/invalid path length"

        if dest_path_length <= 4:
            pytest.skip("base path too long to proceed")

        cases = {
            '': True,
            'a': True,
            'a' * (dest_path_length - 1): True,
            'a' * dest_path_length: True,
            'a' * (dest_path_length + 1): False,
            'a' * (dest_path_length + 2): False,
            'a' * dest_path_length + '/': True,
            'a' * (dest_path_length + 1) + '/': False,
            'a/a/' + ('a' * (dest_path_length - 4)) + '/': True,
            'a/a/' + ('a' * (dest_path_length - 3)) + '/': False,
            '/var/run/': True,
            '../a': True}

        for case, should_pass in cases.items():
            if should_pass:
                seo.config.verify_esp_path_length(case)
            else:
                with pytest.raises(seo.error.AppException):
                    seo.config.verify_esp_path_length(case)
