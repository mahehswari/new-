# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation
# pylint: disable=bad-option-value,useless-option-value # (no-self-use was removed in pylint 2.14)
# pylint: disable=no-self-use # (pytest stylistic convention)

""" Unittests for ek.py file """

from argparse import Namespace
from pathlib import Path
import conftest
import iut.ek


class TestGetCopyFilter:
    ''' Test get_copy_filter function '''

    def test_copy_filter(self):
        ''' Test get_copy_filter function'''

        output_path = Path(__file__).resolve().parent
        received_filter = iut.ek.get_copy_filter(conftest.repo_root(), output_path)

        result = received_filter('../..', ['dek'])
        assert result is not None


class TestCheckForGitChanges:
    ''' Test check_for_git_changes function '''

    def test_check_for_git_changes(self, caplog):
        ''' Test if check_for_git_changes works correctly if no changes '''

        iut.ek.check_for_git_changes(conftest.repo_root(), None)
        assert len(caplog.records) <= 1


class TestCopyExperienceKits:
    ''' Test copy_experience_kits function '''

    def test_copy_experience_kits(self, tmp_path):
        ''' Test if copy_experience_kits works correctly '''

        platform_cfg = {
            'experience_kits': [{
                'name': 'cewefd',
                'path': str(tmp_path) }],
            'clusters': [
              { 'experience_kit': {
                'name': 'nane' }},
              { 'experience_kit': {
                'name': 'bane2' }}]}

        result = iut.ek.copy_experience_kits(platform_cfg, Namespace(output_path=str(tmp_path)))
        assert result is None
