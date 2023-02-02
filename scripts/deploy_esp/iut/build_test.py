# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation
# pylint: disable=bad-option-value,useless-option-value # (no-self-use was removed in pylint 2.14)
# pylint: disable=no-self-use # (pytest stylistic convention)

""" Unittest file for build.py """

import os
from typing import Iterator
import pytest
import conftest
import iut.build


class TestMakeGitOptions:
    ''' Tests for test_make_git_options function '''

    @pytest.fixture
    def credentials(self) -> Iterator[dict]:
        """ Make up random git credentials """
        yield {'username': conftest.random_identifier(),
               'password': conftest.random_identifier()}

    def _git_options_match(self, git_options, creds):
        return git_options == [
            '--git-user', creds['username'],
            '--git-password', creds['password']]

    def test_make_git_options_correct_data_insert(self, credentials):
        ''' Test if make_git_options return correct data when username and password in input '''

        git_options = iut.build.make_git_options(credentials)
        assert self._git_options_match(git_options, credentials)

    def test_make_git_options_only_username_insert(self, credentials):
        ''' Test if make_git_options raise exception when only username in input '''

        credentials.pop('password')

        with pytest.raises(KeyError):
            iut.build.make_git_options(credentials)

    def test_make_git_options_only_password_insert(self, credentials):
        ''' Test if make_git_options raise exception when only password in input '''

        credentials.pop('username')

        with pytest.raises(KeyError):
            iut.build.make_git_options(credentials)

    def test_make_git_options_another_data_besides_expected_at_end(self, credentials):
        ''' Test if make_git_options return correct data when
            another data besides excepted in input at end
        '''

        credentials = {**credentials,
                       conftest.random_identifier(): conftest.random_identifier()}

        git_options = iut.build.make_git_options(credentials)
        assert self._git_options_match(git_options, credentials)

    def test_make_git_options_another_data_besides_expected_at_begin(self, credentials):
        ''' Test if make_git_options return correct data when
            another data besides excepted in input at begin
        '''

        credentials = {conftest.random_identifier(): conftest.random_identifier(),
                       **credentials}

        git_options = iut.build.make_git_options(credentials)
        assert self._git_options_match(git_options, credentials)

    def test_make_git_options_another_data_besides_expected_between(self, credentials):
        ''' Test if make_git_options return correct data when
            another data besides excepted in input between username and password
        '''

        credentials = {'username': credentials['username'],
                       conftest.random_identifier(): conftest.random_identifier(),
                       'password': credentials['password']}

        git_options = iut.build.make_git_options(credentials)
        assert self._git_options_match(git_options, credentials)

    def test_make_git_options_first_password(self, credentials):
        ''' Test if make_git_options return correct data when first password in input '''

        credentials = {'password': credentials['password'],
                       'username': credentials['username']}

        git_options = iut.build.make_git_options(credentials)
        assert self._git_options_match(git_options, credentials)

    def test_make_git_options_nothing_when_input_is_empty(self):
        ''' Test if make_git_options return correct data when input argument is empty '''

        credentials = {}

        with pytest.raises(KeyError):
            iut.build.make_git_options(credentials)


class TestRemoveEspDirs:
    ''' Tests for remove_esp_dirs function '''

    @pytest.fixture
    def toolchain_cfg(self, tmp_path) -> Iterator[dict]:
        """ Produce a minimal toolchain configuration object together with paths it references """
        esp_dir = conftest.random_identifier()
        esp_out_dir = conftest.random_identifier()
        (tmp_path / esp_dir).mkdir()
        (tmp_path / esp_out_dir).mkdir()
        yield { 'path': { 'part': { 'tmp': {
            'esp': esp_dir,
            'esp_out': esp_out_dir }}}}

    def test_remove_esp_dirs_input_correct(self, tmp_path, toolchain_cfg):
        ''' Test if remove_esp_dirs correctly remove directores when all input data is correct '''

        iut.build.remove_esp_dirs(toolchain_cfg, tmp_path)
        assert not list(tmp_path.iterdir())

    def test_remove_esp_dirs_esp_path_empty(self, tmp_path, toolchain_cfg):
        ''' Test if remove_esp_dirs raise exception when esp path is empty '''

        toolchain_cfg['path']['part']['tmp'].pop('esp')

        with pytest.raises(KeyError):
            iut.build.remove_esp_dirs(toolchain_cfg, tmp_path)

    def test_remove_esp_dirs_esp_out_path_empty(self, tmp_path, toolchain_cfg):
        ''' Test if remove_esp_dirs raise exception when esp_out path is empty '''

        toolchain_cfg['path']['part']['tmp'].pop('esp_out')

        with pytest.raises(KeyError):
            iut.build.remove_esp_dirs(toolchain_cfg, tmp_path)

    def test_remove_esp_dirs_additional_data_in_toolchain_cfg(self, tmp_path, toolchain_cfg):
        ''' Test if remove_esp_dirs correctly remove directiories when in toolchain_cfg are additional data '''

        toolchain_cfg['path']['part']['tmp']['unexpected'] = 'data'
        toolchain_cfg['path']['something'] = 'else'

        iut.build.remove_esp_dirs(toolchain_cfg, tmp_path)

        assert not os.listdir(tmp_path)


class TestBuildService:
    ''' Tests for build_service function '''

    def _mock_toolchain_files(self, tmp_path):
        test_argv_script = (
            '#!/usr/bin/env python3\n'
            'import sys\n'
            f'with open({repr(str(tmp_path / "stdout"))}, "w") as stdout:\n'
            '    stdout.write("\\n".join(sys.argv))\n')

        with open(tmp_path / 'se.yaml', 'w', encoding='utf-8') as se_yaml:
            se_yaml.write('null')
        with open(tmp_path / 'deploy_esp.py', 'w', encoding='utf-8') as deploy_esp:
            deploy_esp.write(test_argv_script)
            os.chmod(deploy_esp.fileno(), 0o555)

    def test_build_service(self, tmp_path):
        ''' Test if build service will run '''

        self._mock_toolchain_files(tmp_path)

        toolchain_cfg = { 'path': { 'full': {
            'toolchain': str(tmp_path),
            'logs': '' }}}

        credentials = {'username': conftest.random_identifier(),
                       'password': conftest.random_identifier()}

        iut.build.build_services(toolchain_cfg=toolchain_cfg,
                                 git_credentials=credentials,
                                 config_path=str(tmp_path / 'se.yaml'))

        with open(tmp_path / 'stdout', encoding='utf-8') as stdout:
            lines = stdout.readlines()
            assert len(lines) == 10
