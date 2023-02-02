# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation
# pylint: disable=bad-option-value,useless-option-value # (no-self-use was removed in pylint 2.14)
# pylint: disable=no-self-use # (pytest stylistic convention)

""" Test for SE Install and Upgrade Toolchain: Create package checksums file """

import subprocess
from typing import Iterator
import pytest
import iut.checksum


METADATA = "metadata.yml"
METAFILES = "metadata.sha"
DATAFILES = "package.sha"


def _mock_toolchain_cfg():
    return { "path": { "part": { "package": {
        "metadata": METADATA,
        "checksum": {
            "datafiles": DATAFILES,
            "metafiles": METAFILES }}}}}


class TestVerifyChecksumFiles:
    """Test case for iut.checksum.verify_checksum_files"""

    @pytest.mark.usefixtures("tmp_path")
    @pytest.fixture(autouse=True)
    def _mock_metadata_directory(self) -> Iterator[None]:
        subprocess.run("""
            set -e
            touch metadata.yml package.sha
            sha256sum metadata.yml > metadata.sha
            sha256sum metadata.sha > package.sha
        """, check=True, shell=True)
        yield

    def test_valid_files(self, caplog):
        """ Test if number of logs is equal to the number of checksum files """

        caplog.set_level("INFO")
        iut.checksum.verify_checksum_files(_mock_toolchain_cfg())
        assert len(caplog.records) == 2

    def test_invalid_toolchain(self):
        """ Test if error wil be raised for invalid toolchain configuration """

        invalid_tlc = [{"product": None}, {True: 1}, {}]
        for tlc in invalid_tlc:
            with pytest.raises(KeyError):
                iut.checksum.verify_checksum_files(tlc)

    def test_no_metafiles(self):
        """ Test if error will be raised for invalid metafiles """

        test_tlc = _mock_toolchain_cfg()
        test_tlc["path"]["part"]["package"]["checksum"]["metafiles"] = ""

        with pytest.raises(iut.error.IutError):
            iut.checksum.verify_checksum_files(test_tlc)

    def test_no_datafiles(self):
        """ Test if error will be raised for invalid datafiles """

        test_tlc = _mock_toolchain_cfg()
        test_tlc["path"]["part"]["package"]["checksum"]["datafiles"] = ""

        with pytest.raises(iut.error.IutError):
            iut.checksum.verify_checksum_files(test_tlc)


class TestCreatePackageChecksumFile:
    """Test case for iut.checksum.create_package_checksum_file"""

    def _mock_nonempty_dir(self):
        subprocess.run("""
            touch pyt_file.py log_file.log
        """, check=True, shell=True)

    def test_empty_dir(self, tmp_path, caplog):
        """ Test if function runs properly for empty dir by checking number of logs equal 1 """

        caplog.set_level("INFO")
        iut.checksum.create_package_checksum_file(_mock_toolchain_cfg(), str(tmp_path))
        assert len(caplog.records) == 1

    def test_nonempty_dir(self, tmp_path, caplog):
        """ Test if function runs properly for nonempty dir by checking number of logs equal 1 """

        caplog.set_level("INFO")
        self._mock_nonempty_dir()
        iut.checksum.create_package_checksum_file(_mock_toolchain_cfg(), str(tmp_path))
        assert len(caplog.records) == 1

    def test_invalid_toolchain(self):
        """Test if error wil be raised for invalid toolchain configuration"""

        invalid_tlc = [{"product": None}, {True: 1}, {}]
        for tlc in invalid_tlc:
            with pytest.raises(KeyError):
                iut.checksum.create_package_checksum_file(tlc, DATAFILES)

    def test_package_lines(self, tmp_path):
        """Check if number of lines in package file is equal to number of files in root folder"""

        self._mock_nonempty_dir()
        iut.checksum.create_package_checksum_file(_mock_toolchain_cfg(), str(tmp_path))
        with open(tmp_path / DATAFILES) as datafiles:
            num_pkg_lines = len(list(datafiles))
        assert num_pkg_lines == 2


class TestCreateMetadataChecksumFile:
    """Test case for iut.checksum.create_metadata_checksum_file"""

    @staticmethod
    def _mock_metadata_directory():
        subprocess.run("""
            set -e
            touch metadata.yml
            echo "datas" > metadata.yml
            touch log_file.log
        """, check=True, shell=True)

    def test_nonexistent_metadata(self, tmp_path):
        """ Test if error will be raised for nonexistent metadata """

        with pytest.raises(iut.error.IutError):
            iut.checksum.create_metadata_checksum_file(_mock_toolchain_cfg(), str(tmp_path))

    def test_existing_metadata(self, tmp_path, caplog):
        """ Test if function runs properly for existing metadata by checking num of logs equal 1 """

        caplog.set_level("INFO")
        self._mock_metadata_directory()
        iut.checksum.create_metadata_checksum_file(_mock_toolchain_cfg(), str(tmp_path))
        assert len(caplog.records) == 1

    def test_invalid_toolchain(self, tmp_path):
        """ Test if error wil be raised for invalid toolchain configuration """

        invalid_tlc = [{"product": None}, {True: 1}, {}]
        for tlc in invalid_tlc:
            with pytest.raises(KeyError):
                iut.checksum.create_metadata_checksum_file(tlc, str(tmp_path))
