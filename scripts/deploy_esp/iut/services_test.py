# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation
# pylint: disable=bad-option-value,useless-option-value # (no-self-use was removed in pylint 2.14)
# pylint: disable=no-self-use # (pytest stylistic convention)

""" Unittest file for services.py file """

import os
import pytest
import conftest
import iut.services
import iut.error


def _mock_toolchain_cfg():
    return {
        'docs': {
            'url': "https://github.com/docker/compose",
            'branch': 'v2',
            'path': '/tmp/docs' },
        'path': {
            'part': {
                'package': {
                    'docs': 'docs' }},
            'full': {
                'toolchain': 'tool',
                'logs': 'logs' }}}


class TestRunEspServices:
    ''' Tests for run_esp_services function '''

    def test_run_esp_services_logging(self, caplog):
        '''Test if run_esp_service generates log info'''

        credentials_to_test = { 'username': conftest.random_identifier(),
                                'password': conftest.random_identifier() }

        with pytest.raises(iut.error.IutError), caplog.at_level('INFO'):
            iut.services.run_esp_services(
                _mock_toolchain_cfg(), credentials_to_test, '')

        assert caplog.records[0].getMessage() == 'Starting the ESP services'


class TestStopEspServices:
    ''' Tests for stop_esp_services function '''

    def test_stop_esp_service_logging_debug(self, caplog):
        '''Test if stop_esp_services generates log debug'''

        with pytest.raises(iut.error.IutError), caplog.at_level('DEBUG'):
            iut.services.stop_esp_services(_mock_toolchain_cfg(), "")

        assert caplog.records[0].getMessage() == 'Stopping ESP services'

    def test_stop_esp_service_not_logging_info(self, caplog):
        '''Test if stop_esp_services does not generates log info because of incorrect data in input'''

        with pytest.raises(iut.error.IutError), caplog.at_level('INFO'):
            iut.services.stop_esp_services(_mock_toolchain_cfg(), "")

        assert not caplog.records


class TestRunAnsibleDeployment:
    ''' Tests for run_ansible_deployment function '''

    def _mock_toolchain_files(self, tmp_path):
        test_argv_script = (
            '#!/usr/bin/env python3\n'
            'import sys\n'
            f'with open({repr(str(tmp_path / "stdout"))}, "w") as stdout:\n'
            '    stdout.write("\\n".join(sys.argv))\n')

        with open(tmp_path / 'deploy.py', 'w', encoding='utf-8') as deploy:
            deploy.write(test_argv_script)
            os.chmod(deploy.fileno(), 0o555)

    def test_run_ansible_deployment(self, tmp_path, caplog):
        ''' Test if run_ansible_deployment run correctly '''

        self._mock_toolchain_files(tmp_path)
        toolchain_cfg = { 'path': { 'full': { 'repo': '' }}}
        platform_cfg = { 'experience_kits': [{ 'path': str(tmp_path) }]}

        with caplog.at_level('DEBUG'):
            iut.services.run_ansible_deployment(toolchain_cfg, platform_cfg)

        assert len(caplog.records) == 1
