# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation
# pylint: disable=bad-option-value,useless-option-value # (no-self-use was removed in pylint 2.14)
# pylint: disable=no-self-use # (pytest stylistic convention)

""" Test file for monitoring.py file """

import shutil
import subprocess
from typing import Iterator
import pytest
import requests # pylint: disable=import-error
import iut.monitoring
import iut.error


if not shutil.which('docker'):
    pytest.skip('docker is required to run these tests', allow_module_level=True)


@pytest.fixture(scope='session')
def mock_monitoring_service_image() -> Iterator[str]:
    ''' Build a replacement for the monitoring service image that exits immediately without error. Return its hash '''
    proc = subprocess.run(['docker', 'build', '-'], check=True, text=True, capture_output=True, input='''
        FROM alpine
        ENTRYPOINT true
    ''')
    image_hash = proc.stdout.splitlines()[-1].split(' ')[-1] # last line should read 'Successfully built 1234567890ab'
    yield image_hash
    subprocess.run(['docker', 'rmi', image_hash], check=False)


@pytest.fixture(autouse=True)
# pylint: disable=redefined-outer-name
def dont_touch_actual_monitoring_containers(mock_monitoring_service_image, monkeypatch) -> Iterator[None]:
    ''' Monkeypatch iut.monitoring._SERVICE_TAG so our test functions can't ruin actual deployment container state '''
    monkeypatch.setattr(iut.monitoring, '_SERVICE_TAG', mock_monitoring_service_image)
    yield


class TestBuildService:
    ''' Tests for build_service function '''

    def test_build_service_incorrect_input(self):
        ''' Test if build_service raise exception when data in input is incorrect '''

        toolchain_cfg = {
            'path': {
                'part': {
                    'package': {
                        'docs': 'docs' },
                    'monitoring_service': 'mon_serv' },
                'full': {
                    'toolchain': 'tool',
                    'logs': 'logs',
                    'repo': 'repo' }}}

        with pytest.raises(iut.error.IutError):
            iut.monitoring.build_service(toolchain_cfg)


class TestRetriveMachineData:
    ''' Tests for retrieve_machine_data '''

    def test_retrive_machine_data(self):
        ''' Test if retrieve_machine_data will send request and return an exception '''

        machines = [{
            'bmc': {
                'address': 'address.invalid',
                'username': 'user',
                'password': 'pass' },
            'name': 'nam' }]

        with pytest.raises(requests.exceptions.ConnectionError):
            iut.monitoring.retrieve_machine_data(machines)


class TestRegisterMachines:
    ''' Tests for register_machines function '''

    def test_register_machines(self):
        ''' Test if register_machines will send request and return an exception '''

        machines = [{ 'id': '001' }]
        service = {
            'schema': 'http',
            'addr': 'address.invalid',
            'port': 12345 }

        with pytest.raises(iut.error.IutError):
            iut.monitoring.register_machines(machines, service)


class TestSaveService:
    ''' Tests for save_service function '''

    def _write_save_file(self, tmp_path):
        with open(tmp_path / 'save.txt', 'w', encoding='utf-8'):
            pass

    def test_save_service(self, tmp_path, caplog):
        ''' Test save_service function '''

        self._write_save_file(tmp_path)
        toolchain_cfg = { 'path': { 'part': { 'package': {
            'monitoring_service': str(tmp_path / 'save.txt') }}}}

        with caplog.at_level('INFO'):
            iut.monitoring.save_service(toolchain_cfg, package_path='')

        assert caplog.records[0].getMessage() == 'Saved the monitoring service container image'


class TestStopServices:
    ''' Test for stop_services function '''

    def test_stop_services(self, caplog):
        ''' Test if stop_services will generate one log level info '''

        with caplog.at_level('INFO'):
            iut.monitoring.stop_services()

        assert len(caplog.records) == 1


class TestRunService:
    ''' Test for run_service function '''

    def test_run_service(self):
        ''' Test if run_service function works correctly '''

        result = iut.monitoring.run_service(publish_port=0)

        assert result is not None


class TestExtractMachineList:
    """ Test case for iut.monitoring.extract_machine_list"""

    def test_valid_config(self):
        """ Test if valid platform config will return non-empty list """

        platform_cfg = {
            "clusters": [{
                "name": "cluster1",
                "hosts": {
                    "tmp_host": [{
                        "bmc": {
                            "name": "bmc_name",
                            "username": "bmc_username",
                            "password": "bmc_password" },
                        "name": "controller" }],
                    "tmp_host2": [{
                        "bmc": {
                            "name": "bmc_name2",
                            "username": "bmc_username2",
                            "password": "bmc_password2" },
                        "name": "controller2" }]}}]}

        machines_list = iut.monitoring.extract_machine_list(platform_cfg)

        assert len(machines_list) == 2

    def test_invalid_config(self):
        """ Test if invalid config raise an assertion """

        for invalid_platform_cfg in ({}, []):
            with pytest.raises((KeyError, TypeError)):
                iut.monitoring.extract_machine_list(invalid_platform_cfg)
