# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation
# pylint: disable=bad-option-value,useless-option-value # (no-self-use was removed in pylint 2.14)
# pylint: disable=no-self-use # (pytest stylistic convention)
# pylint: disable=redefined-outer-name # (mock_toolchain_cfg)

""" Test for monitoring service interaction functions """

import os
from pathlib import Path
from typing import Iterator
import pytest
import conftest
import iut.metadata


INVALID_TOOLCHAINS = ({"product": None}, {"name": None}, {True: 1})


@pytest.fixture
def mock_toolchain_cfg() -> Iterator[dict]:
    """ Create a testing toolchain config with a randomized metadata file value """
    yield {
        "path": {
            "part": {
                "package": {
                    "metadata": f"{conftest.random_identifier()}.yml" }}},
        "product": {
            "name": "test_product",
            "version": "1.0-dev" }}


class TestGetPath:
    """Test case for iut.metadata.get_path"""

    def test_valid_path(self, tmp_path, mock_toolchain_cfg):
        """Test if path is properly created"""

        check_path = iut.metadata.get_path(mock_toolchain_cfg, str(tmp_path))
        assert check_path == str(tmp_path / mock_toolchain_cfg["path"]["part"]["package"]["metadata"])

    def test_invalid_toolchain(self, tmp_path):
        """Test if error wil be raised for invalid toolchain configuration"""

        for invalid_toolchain_cfg in INVALID_TOOLCHAINS:
            with pytest.raises((KeyError, TypeError)):
                iut.metadata.create_file(invalid_toolchain_cfg, tmp_path)


class TestUpdateFile:
    """ Test case for iut.metadata.update_path """

    @pytest.fixture(autouse=True)
    def mock_metadata_file(self, mock_toolchain_cfg, tmp_path) -> Iterator[Path]:
        """ Write vacuous data to the metadata file path indicated by toolchain_cfg. Return its path """
        metadata_path = tmp_path / mock_toolchain_cfg["path"]["part"]["package"]["metadata"]
        with open(metadata_path, "w", encoding="utf-8") as metadata_file:
            metadata_file.write("build: {}")
        yield metadata_path

    def test_info_logs(self, tmp_path, mock_toolchain_cfg, caplog):
        """ Test properly executed function by getting a number of info logs equal 1 """

        with caplog.at_level("INFO"):
            iut.metadata.update_file(mock_toolchain_cfg, tmp_path)
        assert len(caplog.records) == 1

    def test_invalid_toolchain(self, tmp_path):
        """ Test if error wil be raised for invalid toolchain configuration """

        for invalid_toolchain_cfg in INVALID_TOOLCHAINS:
            with pytest.raises((KeyError, TypeError)):
                iut.metadata.update_file(invalid_toolchain_cfg, tmp_path)

class TestCreateFile:
    """ Test case for iut.metadata.create_file """

    def test_valid_toolchain(self, tmp_path, mock_toolchain_cfg):
        """ Test if file is properly created """

        iut.metadata.create_file(mock_toolchain_cfg, tmp_path)
        metadata_path = tmp_path / mock_toolchain_cfg['path']['part']['package']['metadata']
        assert metadata_path.is_file()

    def test_invalid_toolchain(self, tmp_path):
        """ Test if error wil be raised for invalid toolchain configuration """

        for invalid_toolchain_cfg in INVALID_TOOLCHAINS:
            with pytest.raises((KeyError, TypeError)):
                iut.metadata.create_file(invalid_toolchain_cfg, tmp_path)

    def test_no_warning_logs(self, tmp_path, mock_toolchain_cfg, caplog):
        """ Test if iut.metadata.create_file passes silently without logging any warnings """

        os.chdir(conftest.repo_root())
        with caplog.at_level("WARNING"):
            iut.metadata.create_file(mock_toolchain_cfg, tmp_path)
        assert not caplog.records
