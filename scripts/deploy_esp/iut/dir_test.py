# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation
# pylint: disable=bad-option-value,useless-option-value # (no-self-use was removed in pylint 2.14)
# pylint: disable=no-self-use # (pytest stylistic convention)

""" Test for directory info/creation/removal with business logic utilites """

from pathlib import Path
import subprocess
from typing import Iterator
import pytest
import iut.dir

class TestGetTrackedDirsFiles:
    """Test case for iut.dir.system.get_tracked_dirs_files"""

    TRACKED = {".gitignore", "scr1.py"}
    UNTRACKED = {"log1", ".git", "scr2.py"}

    @pytest.fixture(autouse=True)
    def mock_git_repo(self, tmp_path) -> Iterator[Path]:
        """ Setup for temporary git repository using for testing """
        subprocess.run("""
            git init > /dev/null
            touch scr1.py scr2.py log1
            echo "log1" > .gitignore 
            git add scr1.py .gitignore
        """, shell=True, check=True)
        yield tmp_path

    def test_tracked_files(self, mock_git_repo):
        """ Test if selected files are properly tracked"""

        git_tracked = {elem.parts[-1] for elem in iut.dir.get_tracked_dirs_files(mock_git_repo)}

        assert git_tracked == TestGetTrackedDirsFiles.TRACKED

    def test_untracked_files(self, mock_git_repo):
        """ Test if selected files are properly untracked """

        full_dir_list = {child.name for child in mock_git_repo.iterdir()}
        git_tracked = {elem.name for elem in iut.dir.get_tracked_dirs_files(mock_git_repo)}

        assert git_tracked == full_dir_list - TestGetTrackedDirsFiles.UNTRACKED

    def test_ignored_files(self, mock_git_repo):
        """ Test if files in .gitignore are properly ignored"""

        with open(mock_git_repo / ".gitignore", encoding="utf-8") as gitignore:
            gitignore_files = {line.strip().rstrip("/") for line in gitignore}

        assert gitignore_files == {"log1"}
