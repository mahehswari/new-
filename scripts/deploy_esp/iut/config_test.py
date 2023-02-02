# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation
# pylint: disable=bad-option-value,useless-option-value # (no-self-use was removed in pylint 2.14)
# pylint: disable=no-self-use # (pytest stylistic convention)

""" Test for SE Install and Upgrade Toolchain configuration related utilities. """

from argparse import Namespace
import json
import os
from pathlib import Path
import shutil
from typing import Iterator, Set, Tuple
import pytest
import conftest
import iut.config


class TestDumpsPlatformCfg:
    """ Test case for iut.config.dumps_platfprm_cfg """

    @pytest.fixture(autouse=True)
    def credentials(self) -> Iterator[dict]:
        """ Make up a pair of random credential data """
        yield {"username": conftest.random_identifier(),
               "password": conftest.random_identifier()}

    def test_censor_accounts(self, credentials):
        """ Test if password in accounts will be replaced """

        config = { "accounts": [credentials] }

        censored = json.loads(iut.config.dumps_platform_cfg(config))
        assert config != censored

    def test_censor_docker(self, credentials):
        """ Test if dockerhub in accounts will be replaced """

        config = { "docker": { "dockerhub": credentials }}

        censored = json.loads(iut.config.dumps_platform_cfg(config))
        assert config["docker"]["dockerhub"] != censored["docker"]["dockerhub"]

    def test_censor_git(self, credentials):
        """ Test if git password will be replaced """

        config = { "git": credentials }

        censored = json.loads(iut.config.dumps_platform_cfg(config))
        assert config["git"] != censored["git"]

    def test_censor_bmc(self, credentials):
        """ Test if bmc password will be replaced """

        config = { "clusters": [{ "hosts": { "xyz": [{ "bmc": credentials }]}}]}

        censored = json.loads(iut.config.dumps_platform_cfg(config))
        assert config != censored

class TestLoadPlatformCfg:
    """ Test case for iut.config.load_platform_cfg """

    def _mock_config_file(self, tmp_path, write_yaml_file=True) -> Namespace:
        config_path = tmp_path / "se.yaml"
        with open(config_path, "w", encoding="utf-8") as config_file:
            if write_yaml_file:
                config_file.write(
                    "experience_kits:\n"
                    "  - name: developer-experience-kit-open\n"
                    "    path: .\n"
                    "\n"
                    "clusters:\n"
                    "  - name: cluster1\n"
                    "    account: default\n"
                    "    experience_kit:\n"
                    "      name: developer-experience-kit-open\n"
                    "      deployment: dek\n"
                    "    hosts:\n"
                    "      controller_group:\n"
                    "        - name: controller\n"
                    "\n"
                    "accounts:\n"
                    "  - name: default\n"
                    "    username: seo\n"
                    "    password: seo\n")
        return Namespace(config_path=config_path)

    def _mock_toolchain_cfg(self):
        return { "path": {
            "part": {
                "data": "iut/data" },
            "full": {
                "repo": Path(__file__).resolve().parents[3] }}}

    def test_valid_data(self, tmp_path):
        """ Test if valid keys are inside returned config"""

        args = self._mock_config_file(tmp_path)
        cfg = iut.config.load_platform_cfg(args, self._mock_toolchain_cfg())
        assert {'experience_kits', 'clusters', 'accounts'} <= set(cfg)

    def test_empty_yaml(self, tmp_path):
        """ Test if error will be raised for empty yaml file"""

        args = self._mock_config_file(tmp_path, write_yaml_file=False)
        with pytest.raises(iut.error.IutError):
            iut.config.load_platform_cfg(args, self._mock_toolchain_cfg())

    def test_nonexistent_yaml(self):
        """ Test if error will be reaised for nonexistent yaml file"""

        args = Namespace(config_path="invalidyamlfile.yaml")
        with pytest.raises(iut.error.IutError):
            iut.config.load_platform_cfg(args, self._mock_toolchain_cfg())

    def test_invalid_toolchain(self, tmp_path):
        """ Test if TypeError will be raised for invald toolchain config"""

        invalid_tlc = self._mock_toolchain_cfg()
        invalid_tlc["path"] = ""
        with pytest.raises(TypeError):
            iut.config.load_platform_cfg(self._mock_config_file(tmp_path), invalid_tlc)


class TestGetGitCredentials:
    """ Test case for iut.config.get_git_credentials """

    def _random_git_credentials(self) -> Namespace:
        return Namespace(
            git_user=conftest.random_identifier(),
            git_password=conftest.random_identifier())

    def _mock_platform_cfg(self):
        return { "git": {
            "username": conftest.random_identifier(),
            "password": conftest.random_identifier() }}

    def test_all_valid_data(self):
        """ Test if creds values will be get from args"""

        args = self._random_git_credentials()

        creds = iut.config.get_git_credentials(self._mock_platform_cfg(), args)
        assert set(creds.values()) == set(vars(args).values())

    def test_empty_cli_args(self):
        """ Test if creds values will be get from platform_cfg """

        args = Namespace(git_user="", git_password="")
        platform_cfg = self._mock_platform_cfg()

        creds = iut.config.get_git_credentials(platform_cfg, args)
        assert set(creds.values()) == set(platform_cfg["git"].values())

    def test_empty_platform_cfg(self):
        """ Test if creds value will be get from args when platform_cfg is empty"""

        args = self._random_git_credentials()
        platform_cfg = {}

        creds = iut.config.get_git_credentials(platform_cfg, args)
        assert set(creds.values()) == set(vars(args).values())

    def test_all_data_empty(self):
        """" Test is creds value will be empty when args and platform_cfg are empty"""

        args = Namespace(git_user=None, git_password="")

        creds = iut.config.get_git_credentials({}, args)
        assert list(creds.values()) == ["", ""]


class TestAddDefaultSettings:
    """ Test case for iut.config.add_default_settings"""

    def _mock_platform_cfg(self):
        return {
            'experience_kits': [{
                'name': 'developer-experience-kit-open',
                'path': '.' }],
            'clusters': [{
                'name': 'cluster1',
                'account': 'default',
                'experience_kit': {
                    'name': 'developer-experience-kit-open',
                    'deployment': 'dek' },
                'hosts': {
                    'controller_group': [{
                        'name': 'controller' }]}}],
            'accounts': [{
                'name': 'smartedge',
                'username': 'smartedge' }]}

    def test_valid_data(self):
        """Test is config will not be changed"""

        cfg = self._mock_platform_cfg()
        iut.config.add_default_settings(cfg)
        assert cfg == self._mock_platform_cfg()

    def test_no_accounts(self, caplog):
        """ Test if default accounts datas will be added"""

        cfg = self._mock_platform_cfg()
        cfg.pop('accounts')

        caplog.at_level("WARNING")
        iut.config.add_default_settings(cfg)
        assert caplog.records

        original_acc_values = set(self._mock_platform_cfg()['accounts'][0].values())
        added_acc_values = set(cfg['accounts'][0].values())
        assert added_acc_values <= original_acc_values

    def test_no_clusters_account(self, caplog):
        """ Test if default clusters account data will be added"""

        cfg = self._mock_platform_cfg()
        cfg['clusters'][0].pop('account')

        caplog.at_level("WARNING")
        iut.config.add_default_settings(cfg)
        assert caplog.records
        assert cfg['clusters'][0]['account'] == cfg['accounts'][0]['name']

    def test_no_all_needed_data(self, caplog):
        """ Test if accounts data and default clusters account data will be added"""

        cfg = self._mock_platform_cfg()
        cfg.pop('accounts')
        cfg['clusters'][0].pop('account')

        caplog.at_level("WARNING")
        iut.config.add_default_settings(cfg)
        assert caplog.records

        added_acc_values = set(cfg['accounts'][0].values())
        added_acc_values.add(cfg['clusters'][0]['account'])

        assert 'smartedge' in added_acc_values

class TestCheckConfigData:
    """ Test case for iut.config.check_config_data"""

    def _mock_valid_platform_cfg(self):
        return {
            'configurations': [{
                'name': 'dek-config',
                'group_vars': True,
                'host_vars': True,
                'sideload': [{
                    'source': 'test',
                    'destination': 'test' }]}],
            'experience_kits': [{
                'name': 'developer-experience-kit-open',
                'path': '.' }],
            'clusters': [{
                'name': 'cluster1',
                'account': 'default',
                'configuration': 'dek-config',
                'experience_kit': {
                    'name': 'developer-experience-kit-open',
                    'deployment': 'dek',
                    'configuration': 'dek-config' },
                'hosts': {
                    'controller_group': [
                      { 'name': 'controller',
                        'address': 'ad',
                        'bmc': {
                            'address': 'ad',
                            'username': 'usr',
                            'password': '<provided>' }},
                      { 'name': 'controller2',
                        'address' : 'ad2',
                        'bmc': {
                            'address': 'ad2',
                            'username': 'usr1',
                            'password': '<provided>' }}]}}],
            'accounts': [{
                'name': 'default',
                'username': 'smartedge',
                'password': 'smartedge' }]}

    def test_valid_config(self):
        """ Test if function runs properly for valid config"""

        iut.config.check_config_data(self._mock_valid_platform_cfg())

    def test_same_bmc_addresses(self):
        """ Test if error will be rased for two the same bmc addresses"""

        cfg = self._mock_valid_platform_cfg()
        cfg['clusters'][0]['hosts']['controller_group'][0]['bmc']['address'] = \
        cfg['clusters'][0]['hosts']['controller_group'][1]['bmc']['address']

        with pytest.raises(iut.error.IutError):
            iut.config.check_config_data(cfg)

    def test_same_host_addresses(self):
        """ Test if error will be rased for two the same host addresses"""

        cfg = self._mock_valid_platform_cfg()
        cfg['clusters'][0]['hosts']['controller_group'][0]['address'] = \
        cfg['clusters'][0]['hosts']['controller_group'][1]['address']

        with pytest.raises(iut.error.IutError):
            iut.config.check_config_data(cfg)

    @staticmethod
    def change_keys_values(dicton: dict, k, val):
        """ Additional function to change values in dict for specific key"""

        for key, value in dicton.items():
            if k in value[0].keys():
                dicton[key][0][k] = val

    def test_none_value_name(self):
        """ Test if error will be raised for name with None value"""

        cfg = self._mock_valid_platform_cfg()

        with pytest.raises(iut.error.IutError):
            self.change_keys_values(cfg, 'name', None)
            iut.config.check_config_data(cfg)

    def test_no_bmc(self):
        """ Test if config without bmc settings is valid"""

        cfg = self._mock_valid_platform_cfg()
        for i in range(2):
            cfg['clusters'][0]['hosts']['controller_group'][i].pop('bmc')

        iut.config.check_config_data(cfg)

    def test_no_host_address(self):
        """ Test if config without host address is valid"""

        cfg = self._mock_valid_platform_cfg()
        for i in range(2):
            cfg['clusters'][0]['hosts']['controller_group'][i].pop('address')

        iut.config.check_config_data(cfg)

    def test_different_account_names(self):
        """ Test if error will be raised for different account names"""

        cfg = self._mock_valid_platform_cfg()
        cfg['accounts'][0]['name'] = 'differentaccountname'

        with pytest.raises(iut.error.IutError):
            iut.config.check_config_data(cfg)

    def test_different_ek_names(self):
        """ Test if error will be raised for different experience kit names"""

        cfg = self._mock_valid_platform_cfg()
        cfg['experience_kits'][0]['name'] = 'differentekname'

        with pytest.raises(iut.error.IutError):
            iut.config.check_config_data(cfg)

    def test_different_configuration_names(self):
        """ Test if error will be raised for different configuration names"""

        cfg = self._mock_valid_platform_cfg()
        cfg['configurations'][0]['name'] = 'differentconfigname'

        with pytest.raises(iut.error.IutError):
            iut.config.check_config_data(cfg)


class TestSetControllerIp:
    """ Test case for iut.config.set_controller_ip """

    @pytest.fixture
    def cluster_name(self) -> Iterator[str]:
        """ Produce a random cluster name """
        yield conftest.random_identifier()

    @pytest.fixture
    def controller_address(self) -> Iterator[str]:
        """ Produce a random controller address """
        yield conftest.random_ipv4()

    @pytest.fixture(autouse=True)
    def mock_inventory_yaml_file(self, tmp_path, request, cluster_name, controller_address) -> Iterator[Path]:
        """ Populate a mock ansible inventory dir inside tmp_path. Return the path to the inventory yaml file """
        group_vars_path = tmp_path / cluster_name / "group_vars" / "all"
        group_vars_path.mkdir(parents=True)
        yaml_path = group_vars_path / "90-settings.yaml"
        with open(yaml_path, "w", encoding="utf-8") as yaml_file:
            if not request.node.get_closest_marker("dont_write_yaml_file"):
                yaml_file.write(
                    "se_controller:\n"
                    f"  address: \"{controller_address}\"\n")
        yield yaml_path

    def test_valid_settings(self, tmp_path, mock_inventory_yaml_file, cluster_name, controller_address):
        ''' Test if address will be overwritten for valid data '''

        iut.config.set_controller_ip(
            cluster_name=cluster_name,
            controller_address=controller_address,
            dst=str(tmp_path))

        with open(mock_inventory_yaml_file, encoding='utf-8') as yaml_file:
            yaml_content = [line.strip() for line in yaml_file.readlines()]
            assert f'address: {controller_address}' in yaml_content

    def test_empty_yaml(self, tmp_path, cluster_name, controller_address, mock_inventory_yaml_file):
        ''' Test if error will be raised for empty yaml file'''

        os.truncate(mock_inventory_yaml_file, 0)
        with pytest.raises(iut.error.IutError):
            iut.config.set_controller_ip(
                cluster_name=cluster_name,
                controller_address=controller_address,
                dst=str(tmp_path))

    def test_invalid_path(self):
        ''' Test if error will be raised for invalid path'''

        with pytest.raises(iut.error.IutError):
            iut.config.set_controller_ip(
                cluster_name='',
                controller_address='',
                dst='')


class TestGenerateProvisioningConfig:
    ''' Test case for iut.config.generate_provisioning_config '''

    @staticmethod
    def _get_unindented_provision_yml(tmp_path) -> list:
        ''' Additional function to get provision.yml content without spaces and new line chars'''
        with open(tmp_path / 'provision.yml', encoding='utf-8') as file:
            return [line.strip() for line in file]

    def _mock_platform_cfg(self, cluster_count=1):
        return {
            'configurations': [{
                'name': 'dek-config',
                'group_vars': True,
                'host_vars': True,
                'sideload': [{
                    'source': 'test',
                    'destination': 'test' }]}],
            'path': {
                'part': {
                    "toolchain" : '/home/seo/repos/dek' }},
            'experience_kits': [{
                'name': 'developer-experience-kit-open',
                'path': '.' }],
            'esp': {
                'url': 'platform url',
                'branch': 'platform branch',
                'dest_dir': 'platform dest dir' },
            'clusters': [
                  { 'name': f'cluster{i + 1}',
                    'account': f'default{i + 1 if i else ""}',
                    'configuration': 'dek-config',
                    'experience_kit': {
                        'name': 'developer-experience-kit-open',
                        'deployment': 'dek',
                        'configuration': 'dek-config' },
                    'hosts': {
                        'controller_group': [{
                            'name': 'controller',
                            'address' : 'ad',
                            'bmc': {
                                'address': 'ad',
                                'username': 'usr',
                                'password': '<provided>' }}]}}
                for i in range(cluster_count)],
            'accounts': [{
                'name': 'default',
                'username': 'smartedge',
                'password': 'smartedge' }]}

    def _mock_toolchain_cfg(self):
        return {
            "context": {
                "offline_flag": False },
            "path": {
                "part": {
                    "tmp": {
                        "esp": "", # no ESP in toolchain_cfg.json
                        "esp_out": "deploy_esp_out" },
                    "toolchain": '' },
                "full": {
                    "repo" : "testrepo" }},
            "profile": {
                "name": "test name",
                "url": "test url",
                "path": "test_path" }}

    def test_additional_cluster_without_force_flag(self, tmp_path):
        """ Test if error will be raised for additional cluster force flag set on false"""

        platform_cfg = self._mock_platform_cfg(cluster_count=2)

        with pytest.raises(iut.error.IutError):
            iut.config.generate_provisioning_config(
                self._mock_toolchain_cfg(), platform_cfg, Namespace(force_flag=False), str(tmp_path))

    def test_additional_cluster_with_force_flag(self, tmp_path):
        """ Test if file wil be created for force flag set on true"""

        platform_cfg = self._mock_platform_cfg(cluster_count=2)

        iut.config.generate_provisioning_config(
            self._mock_toolchain_cfg(), platform_cfg, Namespace(force_flag=True), str(tmp_path))

        assert (tmp_path / 'provision.yml').stat().st_size

    def test_esp_in_platform(self, tmp_path):
        """ Test if provision esp data will be the same as in platform config"""

        platform_cfg = self._mock_platform_cfg()

        iut.config.generate_provisioning_config(
            self._mock_toolchain_cfg(), platform_cfg, Namespace(force_flag=False), str(tmp_path))

        yml_content = self._get_unindented_provision_yml(tmp_path)
        esp_items = set(f'{key}: {value}' for key, value in platform_cfg['esp'].items())
        assert esp_items <= set(yml_content)

    def test_esp_in_toolchain(self, tmp_path):
        """ Test if provision esp data will be the same as in toolchain config """

        platform_cfg = self._mock_platform_cfg()
        platform_cfg.pop('esp')
        toolchain_cfg = self._mock_toolchain_cfg()
        toolchain_cfg['path']['part']['toolchain'] = str(tmp_path)

        with open(tmp_path / 'default_config.yml', 'w', encoding="utf-8") as yml_file:
            yml_file.write(
                'esp:\n'
                '  url: tlc url\n'
                '  branch: tlc branch\n')

        iut.config.generate_provisioning_config(
            toolchain_cfg, platform_cfg, Namespace(force_flag=False), str(tmp_path))

        with open(tmp_path / 'default_config.yml', encoding='utf-8') as default:
            default_content = set(default)
        with open(tmp_path / 'provision.yml', encoding='utf-8') as provision:
            provision_content = set(provision)

        assert default_content <= provision_content

    def test_no_esp(self, tmp_path):
        """ Test if error will be rased for no esp in tlc and platform config"""

        platform_cfg = self._mock_platform_cfg()
        platform_cfg.pop('esp')
        toolchain_cfg = self._mock_toolchain_cfg()
        toolchain_cfg['path']['part']['toolchain'] = '/nonexistentpath'

        with pytest.raises(iut.error.IutError):
            iut.config.generate_provisioning_config(
                toolchain_cfg, platform_cfg, Namespace(force_flag=False), tmp_path)

    def test_docker_in_platform(self, tmp_path):
        """ Test if provision docker data will be the same as in platform config """

        platform_cfg = self._mock_platform_cfg()
        platform_cfg['docker'] = { 'registry_mirrors': [f'http://{conftest.random_ipv4()}:443'] }

        iut.config.generate_provisioning_config(
            self._mock_toolchain_cfg(), platform_cfg, Namespace(force_flag=False), tmp_path)

        yml_content = self._get_unindented_provision_yml(tmp_path)
        for key, value in platform_cfg['docker'].items():
            assert f'{key}:' in yml_content
            assert f'- {value[0]}' in yml_content

    def test_no_docker_in_platform(self, tmp_path):
        """ Test if provision docker data will have default empty array"""

        iut.config.generate_provisioning_config(
            self._mock_toolchain_cfg(), self._mock_platform_cfg(), Namespace(force_flag=False), tmp_path)

        yml_content = self._get_unindented_provision_yml(tmp_path)
        assert 'registry_mirrors: []' in yml_content

    def test_dockerhub_in_platform(self, tmp_path):
        """ Test if provision dockerhub data will be the same as in platform config """

        platform_cfg = self._mock_platform_cfg()
        platform_cfg['docker'] = { 'dockerhub': {
                'username': 'dockerhub username',
                'password': '<provided>' }}

        iut.config.generate_provisioning_config(
            self._mock_toolchain_cfg(), platform_cfg, Namespace(force_flag=False), tmp_path)

        yml_content = self._get_unindented_provision_yml(tmp_path)
        for key, value in platform_cfg['docker']['dockerhub'].items():
            assert f'{key}: {value}' in yml_content

    def test_git_in_platform(self, tmp_path):
        """ Test if provision git data will be the same as in platform config  """

        platform_cfg = self._mock_platform_cfg()
        platform_cfg['git'] = {
            'username': 'gituser',
            'password': '<provided>' }

        iut.config.generate_provisioning_config(
            self._mock_toolchain_cfg(), platform_cfg, Namespace(force_flag=False), tmp_path)

        yml_content = self._get_unindented_provision_yml(tmp_path)
        for key, value in platform_cfg['git'].items():
            if key == 'username':
                key = 'user'
            assert f'{key}: {value}' in yml_content

    def test_profile_path(self, tmp_path):
        """ Test if path will be added to provision file except url and branch"""

        toolchain_cfg = self._mock_toolchain_cfg()
        toolchain_cfg['profile'].pop('url')

        iut.config.generate_provisioning_config(
            toolchain_cfg, self._mock_platform_cfg(), Namespace(force_flag=False), tmp_path)

        yml_content = self._get_unindented_provision_yml(tmp_path)
        path = Path(toolchain_cfg["path"]["full"]["repo"], toolchain_cfg["profile"]['path'])
        assert f'path: {path}' in yml_content

    def test_monitoring_machine(self, tmp_path):
        """ Test if monitoring machine setting will be added to yml file"""

        name = conftest.random_identifier()
        id_ = conftest.random_identifier()
        mac = conftest.random_mac()
        monitoring_machines = [{
            "name": name,
            "macs": [mac],
            "id" : id_ }]

        iut.config.generate_provisioning_config(
            self._mock_toolchain_cfg(), self._mock_platform_cfg(), Namespace(force_flag=False), tmp_path,
            monitoring_machines=monitoring_machines)

        yml_content = self._get_unindented_provision_yml(tmp_path)
        assert {f'- name: {name}',
                f'- {mac}',
                f'machine_id: {id_}'} <= set(yml_content)


class TestGenerateAnsibleConfiguration:
    """ Test case for iut.config.generate_ansible_configuration"""

    @staticmethod
    def _walk_dir(path) -> Iterator[Tuple[Path, Set[str]]]:
        """ Wrap os.walk so that it returns (path, contents) tuples """
        return ((Path(path), set(filenames)) for path, _, filenames in os.walk(path))

    @pytest.fixture
    def mock_development_kit(self, tmp_path) -> Iterator[Path]:
        """ Create a minimal copy of the development kit. Return its subpath """
        repo_root = conftest.repo_root()

        tmp_kit_path = tmp_path / conftest.random_identifier()
        tmp_kit_path.mkdir()
        shutil.copytree(repo_root / 'inventory',
                        tmp_kit_path / 'inventory')
        deployment_path = tmp_kit_path / 'deployments' / 'dek'
        deployment_path.mkdir(parents=True)
        profile_path = tmp_kit_path / 'platform_profiles' / 'prof1'
        profile_path.mkdir(parents=True)

        with open(deployment_path / 'all.yml', 'w', encoding='utf-8') as yml_file:
            yml_file.write('name: additional file')
        with open(profile_path / 'all.yml', 'w', encoding='utf-8') as yml_file:
            yml_file.write('name: additional file')

        yield tmp_kit_path

    @pytest.fixture
    def random_destdir(self, tmp_path) -> Iterator[Path]:
        """ Randomize a destination path for generate_ansible_configuration """
        yield tmp_path / conftest.random_identifier()

    def _mock_platform_cfg(self):
        return {
            'configurations': [{
                'name': 'dek-config',
                'group_vars': {
                    'groups' : None },
                'host_vars': {
                    'hosts': None },
                'sideload': [{
                    'source': 'test',
                    'destination': 'test' }]}],
            "path": {
                "part": {
                    "toolchain" : '' }},
            'experience_kits': [{
                'name': 'developer-experience-kit-open',
                'path': '.' }],
            'esp' : {
                'url': 'platform url',
                'branch': 'platform branch',
                'dest_dir': 'platform dest dir' },
            'clusters': [{
                'name': conftest.random_identifier(),
                'account': 'default',
                'configuration': 'dek-config',
                'experience_kit': {
                    'name': 'developer-experience-kit-open',
                    'configuration': 'dek-config' },
                'hosts': {
                    'controller_group': [{
                        'name': 'controller',
                        'address' : 'ad',
                        'bmc': {
                            'address': 'ad',
                            'username': 'usr',
                            'password': '<provided>' }}],
                    'edgenode_group': [] }}],
            'accounts': [{
                'name': 'default',
                'username': 'smartedge',
                'password': 'smartedge' }]}

    def test_nonexistent_path(self, tmp_path, random_destdir, caplog):
        """ test is error will be raised for nonexistent kit path"""

        with pytest.raises(FileNotFoundError), caplog.at_level("DEBUG"):
            iut.config.generate_ansible_configuration(
                self._mock_platform_cfg(), str(tmp_path / 'nonexistent-path'), str(random_destdir))
        assert len(caplog.records) == 3

    def test_unremovable_path(self, mock_development_kit, caplog):
        """ Test if error will be raised for unremovable destination path"""

        with pytest.raises(iut.error.IutError), caplog.at_level("DEBUG"):
            iut.config.generate_ansible_configuration(
                self._mock_platform_cfg(), str(mock_development_kit), '/dev/null')
        assert len(caplog.records) == 1

    def test_valid_data(self, random_destdir, mock_development_kit):
        """Test if for valid data file will be created and have content"""

        platform_cfg = self._mock_platform_cfg()
        iut.config.generate_ansible_configuration(
            platform_cfg, str(mock_development_kit), str(random_destdir))

        inv_file_path = random_destdir / platform_cfg['clusters'][0]['name'] / 'inventory.yaml'
        assert inv_file_path.stat().st_size

    def test_nonempty_host_vars(self, tmp_path, random_destdir, mock_development_kit):
        """ Test if 90-settings.yaml will be created if host_vars is not None"""

        platform_cfg = self._mock_platform_cfg()
        platform_cfg['configurations'][0]['host_vars']['hosts'] = 'dek host'

        iut.config.generate_ansible_configuration(
            platform_cfg, str(mock_development_kit), str(random_destdir))

        hosts_path = random_destdir / platform_cfg['clusters'][0]['name'] / 'host_vars' / 'hosts'
        assert (hosts_path, {'90-settings.yaml'}) in self._walk_dir(tmp_path)

    def test_nonempty_group_vars(self, tmp_path, random_destdir, mock_development_kit):
        """ Test if 90-settings.yaml will be created if group_vars is not None"""

        platform_cfg = self._mock_platform_cfg()
        platform_cfg['configurations'][0]['group_vars']['groups'] = 'dek_groups'

        iut.config.generate_ansible_configuration(
            platform_cfg, str(mock_development_kit), str(random_destdir))

        groups_path = random_destdir / platform_cfg['clusters'][0]['name'] / 'group_vars' / 'groups'
        assert (groups_path, {'90-settings.yaml'}) in self._walk_dir(tmp_path)

    def test_nonempty_deployment(self, tmp_path, random_destdir, mock_development_kit):
        """ Test if 30-deployment.yaml will be created if deployment exists"""

        platform_cfg = self._mock_platform_cfg()
        platform_cfg['clusters'][0]['experience_kit']['deployment'] = 'dek'

        iut.config.generate_ansible_configuration(
            platform_cfg, str(mock_development_kit), str(random_destdir))

        groups_all_path = random_destdir / platform_cfg['clusters'][0]['name'] / 'group_vars' / 'all'
        assert (groups_all_path, {'10-default.yml', '30-deployment.yaml'}) in self._walk_dir(tmp_path)

    def test_nonempty_platform_profile(self, tmp_path, random_destdir, mock_development_kit):
        """ Test if 40-platform-profile.yaml will be created if platform-profile exists """

        platform_cfg = self._mock_platform_cfg()
        platform_cfg['clusters'][0]['platform-profile'] = 'prof1'

        iut.config.generate_ansible_configuration(
            platform_cfg, str(mock_development_kit), str(random_destdir))

        groups_all_path = random_destdir / platform_cfg['clusters'][0]['name'] / 'group_vars' / 'all'
        assert (groups_all_path, {'10-default.yml', '40-platform-profile.yaml'}) in self._walk_dir(tmp_path)

    def test_edgenode_exists(self, random_destdir, mock_development_kit):
        """ Test if non-empty egdenode_group will add another values to yml file"""

        platform_cfg = self._mock_platform_cfg()
        platform_cfg['clusters'][0]['hosts']['edgenode_group'] = [{
            'name': 'node01',
            'address' : 'ad2',
            'bmc': {
                'address': 'ad2',
                'username': 'usr2',
                'password': '<provided>' }}]

        iut.config.generate_ansible_configuration(
            platform_cfg, str(mock_development_kit), str(random_destdir))

        inv_file_path = random_destdir / platform_cfg['clusters'][0]['name'] / 'inventory.yaml'
        with open(inv_file_path, encoding="utf-8") as inv_file:
            inv_lines = {line.strip() for line in inv_file}
        assert {'ansible_host: ad2', 'single_node_deployment: false', 'node01:'} <= inv_lines

    def test_no_controller_address(self, random_destdir, mock_development_kit, caplog):
        """Test if no address for controller group will assert warnings"""

        platform_cfg = self._mock_platform_cfg()
        platform_cfg['clusters'][0]['hosts']['controller_group'][0].pop('address')
        platform_cfg['clusters'][0]['hosts']['edgenode_group'] = [{
            'name': 'node01',
            'address' : 'ad2',
            'bmc': {
                'address': 'ad2',
                'username': 'usr2',
                'password': '<provided>' }}]

        with caplog.at_level('WARNING'):
            iut.config.generate_ansible_configuration(
                platform_cfg, str(mock_development_kit), str(random_destdir))
        assert len(caplog.records) == 2


class TestGenerateDeploymentConfiguration:
    """ Test case for iut.config.generate_deployment_configuration"""

    @pytest.fixture(autouse=True)
    def mock_repo_root(self, tmp_path) -> Iterator[None]:
        """ Copy just the ansible inventory to a fake repo-like destination """
        shutil.copytree(conftest.repo_root() / 'inventory',
                        tmp_path / 'inventory')
        yield

    def _mock_platform_cfg(self) -> dict:
        return {
            'configurations': [{
                'name': 'dek-config',
                'group_vars': {
                    'groups' : 'group',
                    'all': {
                        'se_controller': {
                            'address': 'aaaaaaaaaaaaaa' }}},
                'host_vars': {
                    'hosts': 'host' },
                'sideload': [{
                    'source': 'test',
                    'destination': 'test' }]}],
            "path": {
                "part": {
                    "toolchain": '' }},
            'experience_kits': [{
                'name': 'developer-experience-kit-open',
                'path': '' }],
            'esp' : {
                'url': 'platform url',
                'branch': 'platform branch',
                'dest_dir': 'platform dest dir' },
            'clusters': [{
                'name': 'cluster1',
                'account': 'default',
                'configuration': 'dek-config',
                'experience_kit': {
                    'name': 'developer-experience-kit-open',
                    'configuration': 'dek-config',
                    'deployment': "controller" },
                'hosts': {
                    'controller_group': [{
                        'name': 'controller',
                        'address' : 'ad',
                        'bmc': {
                            'address': 'ad',
                            'username': 'usr',
                            'password': '<provided>' }}]}}],
            'accounts': [{
                'name': 'default',
                'username': 'smartedge',
                'password': 'smartedge' }]}

    def _mock_toolchain_cfg(self):
        return {
            'path': {
                'full': {
                    'repo': '' }},
            'product': {
                'codename' : 'test' }}

    def test_no_address(self, tmp_path):
        """ Test if error will be raised for no address and virgo codename"""

        platform_cfg = self._mock_platform_cfg()
        toolchain_cfg = self._mock_toolchain_cfg()
        toolchain_cfg['product']['codename'] = 'virgo'
        toolchain_cfg['path']['full']['repo'] = tmp_path
        platform_cfg['clusters'][0]['hosts']['controller_group'][0]['address'] = None

        with pytest.raises(iut.error.IutError):
            iut.config.generate_deployment_configuration(toolchain_cfg, platform_cfg)

    def test_exist_deployment_controller_no_address(self, tmp_path):
        """ Test if function runs properly for valid config but no virgo codename"""

        platform_cfg = self._mock_platform_cfg()
        toolchain_cfg = self._mock_toolchain_cfg()
        toolchain_cfg['path']['full']['repo'] = tmp_path
        platform_cfg['clusters'][0]['hosts']['controller_group'][0]['address'] = None

        iut.config.generate_deployment_configuration(toolchain_cfg, platform_cfg)

    def test_exist_deployment_node(self, tmp_path):
        """ Test if yml file will be created for exist node settings in platform_cfg"""

        platform_cfg = self._mock_platform_cfg()
        toolchain_cfg = self._mock_toolchain_cfg()
        toolchain_cfg['product']['codename'] = 'virgo'
        platform_cfg['experience_kits'][0]['path'] = tmp_path
        platform_cfg['clusters'][0]['hosts']['controller_group'][0]['address'] = tmp_path
        platform_cfg['clusters'].append({
            'name': 'node01',
            'account': 'default',
            'configuration': 'dek-config',
            'experience_kit': {
                'name': 'developer-experience-kit-open',
                'configuration': 'dek-config',
                'deployment': 'node' },
            'hosts': {
                'controller_group': [{
                    'name': 'node01',
                    'address' : tmp_path,
                    'bmc': {
                        'address': 'ad',
                        'username': 'usr',
                        'password': '<provided>' }}]}})

        created_file = (tmp_path
                       / 'inventory'
                       / 'automated'
                       / platform_cfg['clusters'][1]['name']
                       / 'group_vars'
                       / 'all'
                       / '90-settings.yaml')

        iut.config.generate_deployment_configuration(toolchain_cfg, platform_cfg)
        assert created_file.stat().st_size
