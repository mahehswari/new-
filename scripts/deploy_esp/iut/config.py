# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

""" SE Install and Upgrade Toolchain configuration related utilities. """

import subprocess # nosec B404
import collections
import copy
import glob
import json
import logging
import os
import shutil

import seo.config
import seo.yaml
import seo.error
import iut.error
import iut.slo.config


FORCE_OPT = "--force"


def create_common_argument_group(parser, package_root):
    """Create a common argument group in the scope of the provided argument parser.

       Return the created group
    """

    g = parser.add_argument_group("common arguments")

    default_config_path = os.path.relpath(os.path.join(package_root, "se.yaml"))

    g.add_argument(
        "-c", "--config", action="store", dest="config_path", metavar="PATH", default=default_config_path,
        help="""
            PATH to the platform configuration file; it's a top level config file adjusting the installation
            process parameters; a new config file can be generated using the se_config.py command
            (default: %(default)s)
            """)

    iut.slo.config.add_debug_argument(g)

    g.add_argument(
        "-f", FORCE_OPT, action="store_true", dest="force_flag",
        help="""
            force the script to go over the errors it can fix automatically; use this option with caution as it may
            override multiple warnings and errors at once; it is safer to resolve manually each of the issues the
            script complains about
            """)

    g.add_argument(
        "--tmp-dir", action="store", metavar="PATH", dest="tmp_dir_path", default=".",
        help="directory to create a temporary directory in (default: %(default)s)")

    iut.slo.config.add_help_argument(g)

    return g


def create_auth_argument_group(parser, toolchain_cfg):
    """Create an authentication argument group in the scope of the provided argument parser.

        Parameters:
            parser - the parser to add the group to
            toolchain_cfg - the toolchain configuration data as provided to the main function

       Return the created group
    """

    product_name = toolchain_cfg["product"]["name"]

    g = parser.add_argument_group("authentication arguments")

    g.add_argument(
        "--git-user", action="store", dest="git_user", metavar="NAME",
        help=f"NAME of the git remote user to be used to clone required {product_name} repositories")

    g.add_argument(
        "--git-password", action="store", dest="git_password", metavar="VALUE",
        help=f"Git remote token to be used to clone required {product_name} repositories")

    return g


def load_platform_cfg(args, toolchain_cfg):
    """ Load and validate specified platform configuration file

        Parameters:
            config_path - path to the configuration file to be handled
            toolchain_cfg - the toolchain configuration data as provided to the main function
    """
    config_path = args.config_path

    try:
        cfg = seo.yaml.load(config_path) # nosec - B506 (project specific wrapper, safe_load used internally)
    except seo.error.AppException as e:
        if e.code == iut.error.Codes.FILE_OPEN_ERROR:
            raise iut.error.IutError(
                e.code,
                "IUT-1",
                f"Failed to load the '{os.path.relpath(config_path)}' platform configuration file:\n"
                f"    {e.inner_msg}")

        raise iut.error.IutError(
            e.code,
            "IUT-2",
            f"Failed to parse the '{os.path.relpath(config_path)}' platform configuration file:\n"
            f"{seo.yaml.indent_error_msg(e.inner_msg)}")

    schema_path = os.path.join(
        toolchain_cfg["path"]["full"]["repo"],
        toolchain_cfg["path"]["part"]["data"],
        "schema", "se_platform_config.json")

    with open(schema_path) as f:
        schema = json.load(f)

    # Fundamental schema validation:
    try:
        seo.config.validate(cfg, config_path, schema, "SE Platform configuration")
    except seo.error.AppException as e:
        raise iut.error.IutError(
            seo.error.Codes.CONFIG_ERROR,
            "IUT-3",
            e.msg)

    # complete default things
    add_default_settings(cfg)

    # data validation
    check_config_data(cfg)

    logging.debug("The SE Platform configuration file ('%s') is valid:\n%s", config_path, dumps_platform_cfg(cfg))

    return cfg


def dumps_platform_cfg(platform_cfg):
    """ Censor all the secret fields of the provided platform config, and return it serialized to JSON string """

    censored = copy.deepcopy(platform_cfg)

    def censor(obj, field="password"):
        if field in obj:
            obj[field] = "<provided>"

    # Censor the platform account passwords:

    for account in censored.get("accounts", []):
        censor(account)

    # Censor the host BMC authentication passwords:

    for cluster in censored.get("clusters", []):
        for _, hosts in cluster.get("hosts", {}).items():
            for host in hosts:
                censor(host.get("bmc", {}))

    censor(censored.get("docker", {}).get("dockerhub", {}))
    censor(censored.get("git", {}))

    return json.dumps(censored, sort_keys=True, indent=4, ensure_ascii=False)


def _generate_provisioning_profile_cfg(toolchain_cfg, account):
    tcc_profile = toolchain_cfg["profile"]

    # Profile configuration
    # Default values for the profile when does not exist in the configuration file (e.g. Minimal Config Example)
    profile = {
        "name": tcc_profile["name"],
        "scenario": "single-node",
        "bare_os": True,
        # Implementation of credentials is temporary because there is no feature to use different accounts credentials
        # in that case we use credentials from the first matched occurrence between 'cluster account'
        # and account definitions
        "account": copy.deepcopy(account)
    }

    if "url" in tcc_profile:
        profile['url'] = tcc_profile["url"]
        profile['branch'] = tcc_profile.get("branch", "feature/install-upgrade-toolchain")
    else:
        profile['path'] = os.path.join(toolchain_cfg["path"]["full"]["repo"], tcc_profile["path"])

    return profile


def _generate_provisioning_docker_cfg(cfg):

    docker = cfg.get('docker', {})

    out_cfg = {
        "registry_mirrors": docker.get("registry_mirrors", [])
    }

    dockerhub = docker.get("dockerhub")

    if dockerhub:
        out_cfg["dockerhub"] = dockerhub.copy()

    return out_cfg

def _generate_git_provisioning_cfg(cfg):
    # @fixme modify deploy_esp so this is not necessary

    out = {}

    if 'username' in cfg['git']:
        out['user'] = cfg['git']['username']

    if 'password' in cfg['git']:
        out['password'] = cfg['git']['password']

    return out

def _generate_hosts_cfg(monitoring_machines):
    return [
        {
            "name": machine["name"],
            "mac": list(machine["macs"]),
            "machine_id": machine["id"],
            "monitoring_enabled": True
        }
        for machine in monitoring_machines
    ]

def _get_esp_from_default_config(toolchain_cfg):
    try:
        default_cfg = seo.yaml.load( # nosec - B506 (project specific wrapper, safe_load used internally)
            os.path.join(
                toolchain_cfg["path"]["part"]["toolchain"], "default_config.yml"
            )
        )
    except seo.error.AppException as e:
        raise iut.error.IutError(
            e.code,
            "IUT-1" if e.code == iut.error.Codes.FILE_OPEN_ERROR else "IUT-2",
            e.msg)

    return default_cfg["esp"]

def generate_provisioning_config(toolchain_cfg, platform_cfg, args, tmp_root, monitoring_machines=None):
    """ Generate provisioning configuration file (IUP/A/11)

        Parameters:
            toolchain_cfg - install and upgrade toolchain config as provided to the main function
            platform_cfg - platform configuration data as returned by the iut.config.load_platform_cfg function
            args - parsed command line arguments object as returned by the parse_args function
    """

    # Esp configuration will be taken from platform config, if it does not exist there
    # then default values for esp will be taken from default_config.yml
    esp = platform_cfg['esp'] if 'esp' in platform_cfg else _get_esp_from_default_config(toolchain_cfg)
    esp['dest_dir'] = os.path.join(tmp_root, toolchain_cfg["path"]["part"]["tmp"]["esp"])

    # Default credentials for the profile (in case of minimal config example)
    account_name = None

    # Collecting a sorted list of cluster account references. The purpose of this guard code is to prevent a situation
    #  in which the user tries to use different account definitions for different clusters. It is currently not
    #  supported by the underlying technology (deploy_esp + profile). Related ticket: ESS-16922
    accounts_ref = []
    for cluster in platform_cfg['clusters']:
        account = cluster.get('account')
        if account and account not in accounts_ref:
            # The account reference is specified, not empty, and seen for the first time.
            accounts_ref.append(account)

    # Looking for the first matched occurrence between [cluster][account] and account definitions
    for account in platform_cfg['accounts']:
        if account['name'] == accounts_ref[0]:
            account_name = account['name']
            the_account = {
                'username': account['username'],
                'password': account['password']
            }
            break

    # Protection against multiple credentials usage for profile
    if len(accounts_ref) >= 2 and not args.force_flag:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR,
            "IUT-X",
            "There is no mechanism for using multiple credentials for hosts,\n" \
            "    if you want to continue with the same credentials for all hosts please use -f/--force flag.")

    if account_name is None:
        msg = "All hosts have default credentials."
    else:
        msg = f"All hosts have the same credentials from ['accounts']['{account_name}']" \
            " filed located in the platform configuration file."
    logging.info(msg)

    profile = _generate_provisioning_profile_cfg(toolchain_cfg, the_account)

    # Template of the generated config
    generated_cfg = {
        'esp': esp,
        'profiles': [profile],
        'docker': _generate_provisioning_docker_cfg(platform_cfg),
        'dnsmasq': {
            'enabled': False,
            'network_dns_primary': '',
            'network_dns_secondary': '',
            'dhcp_range_minimum': '',
            'dhcp_range_maximum': '',
            'network_broadcast_ip': '',
            'network_gateway_ip': '',
            'host_ip': ''
        },
        'usb_images': {
            'build': True,
            'bios': False,
            'efi': True,
            'all_in_one': False,
            'output_path': os.path.join(tmp_root, toolchain_cfg["path"]["part"]["tmp"]["esp_out"])
        },
        'dhcp_client_address_freeze': platform_cfg.get('dhcp_client_address_freeze', False)
    }

    if 'git' in platform_cfg:
        generated_cfg['git'] = _generate_git_provisioning_cfg(platform_cfg)

    if 'ntp_server' in platform_cfg:
        generated_cfg['ntp_server'] = platform_cfg['ntp_server']

    if 'admin_interface' in platform_cfg:
        generated_cfg['admin_interface'] = platform_cfg['admin_interface']

    if monitoring_machines:
        generated_cfg['hosts'] = _generate_hosts_cfg(monitoring_machines)

    # Config file will be created under the path from --tmp-dir argument
    path = os.path.join(tmp_root, "provision.yml")

    seo.yaml.save(generated_cfg, path)

    logging.info("Provisioning configuration file has been generated under the path %s", path)

    return path


class _ansible:
    """Names of ansible groups related to deployments"""
    CPLANE_GROUP = "controller_group"
    EDGENODE_GROUP = "edgenode_group"


def generate_ansible_configuration(cfg, kit_path, destination_path):
    """
    Generates complete configuration for Ansible, inventory and variables, basing on Smart Edge configuration file,
    parsed as cfg.

    Default variables from kit_path/inventory/default will be used as default values by copying files.

    Ansible inventory is generated basing on hosts dictionary from given cluster, address fields for each host
    have to be defined. Target ansible configuration will be placed in destination_path with subdirectories
    named as cluster names.

    Return value is a dictionary mapping cluster name to a directory containing inventory.yaml and variables files.
    """


    default_variables_path = os.path.join(kit_path, "inventory/default")

    try:
        logging.debug("Removing old configuration at %s", destination_path)
        shutil.rmtree(destination_path)
    except OSError as e:
        if isinstance(e, FileNotFoundError) and e.filename == destination_path:
            logging.debug("Old configuration at %s not found", e.filename)
        else:
            raise iut.error.IutError(iut.error.Codes.GENERIC_ERROR,
                "IUT-X", f"Cannot remove file or directory {e.filename}") from e

    logging.debug("Generating ansible configuration at %s", destination_path)

    # configurations can be None, validation stage will verify it first if valid configuration is used in each cluster
    configurations = cfg.get("configurations")

    for cluster in cfg['clusters']:
        cluster_path = os.path.join(destination_path, cluster['name'])
        shutil.copytree(default_variables_path, cluster_path)

        if 'configuration' in cluster['experience_kit']:
            configuration_name = cluster['experience_kit']['configuration']
            configuration = next((c for c in configurations if c['name'] == configuration_name))

            for section in ['group_vars', 'host_vars']:
                if section in configuration:
                    for name, variables in configuration[section].items():
                        if variables:
                            file_name = os.path.join(cluster_path, section, name, "90-settings.yaml")
                            os.makedirs(os.path.dirname(file_name), exist_ok=True)
                            seo.yaml.save(variables, file_name)

        if 'deployment' in cluster['experience_kit']:
            path = os.path.join(kit_path, "deployments", cluster['experience_kit']['deployment'], "*.yml")

            filenames = glob.glob(path)

            for src in filenames:
                group_name = os.path.splitext(os.path.basename(src))[0]
                dst = os.path.join(cluster_path, "group_vars", group_name, "30-deployment.yaml")
                shutil.copy(src, dst)

        if 'platform-profile' in cluster:
            path = os.path.join(kit_path, "platform_profiles", cluster['platform-profile'], "*.yml")

            filenames = glob.glob(path)

            for src in filenames:
                group_name = os.path.splitext(os.path.basename(src))[0]
                dst = os.path.join(cluster_path, "group_vars", group_name, "40-platform-profile.yaml")
                shutil.copy(src, dst)

        # now go with inventory.yaml
        account = next((a for a in cfg['accounts'] if a['name'] == cluster['account']))

        edgenode_group = cluster['hosts'].get(_ansible.EDGENODE_GROUP)
        # singlenode happens when edgenode_group is not defined or there is a single link entry in edgenode_group
        singlenode = not edgenode_group or len(edgenode_group) == 1 and len(edgenode_group[0].keys()) == 1

        variables = { "cluster_name": cluster['name'],
                      "single_node_deployment": singlenode,
                      "limit": "" }

        if 'deployment' in cluster['experience_kit']:
            variables['deployment'] = cluster['experience_kit']['deployment']

        inventory = { "all": { "vars": variables }}

        inventory_hosts = {}
        # first build hosts list to get links working
        for group, hosts in cluster['hosts'].items():
            for host in hosts:
                if 'address' in host:
                    inventory_hosts[host['name']] = host

        link_id = 0
        for group, hosts in cluster['hosts'].items():
            group_hosts = {}

            for host in hosts:
                if len(host.keys()) == 1: # host is a link
                    host = copy.deepcopy(inventory_hosts[host['name']])
                    host['name'] += f"_link_{link_id}"
                    link_id += 1

                if 'address' in host:
                    ansible_host = {"ansible_host": host['address'],
                                    "ansible_user": account['username'] }
                    group_hosts[host['name']] = ansible_host
                else:
                    logging.warning("Host %s has no address, it will be ignored.", host['name'])

            inventory[group] = {"hosts": group_hosts}

        if not list(inventory[_ansible.CPLANE_GROUP]['hosts'].keys()):
            logging.error("CPLANE group is empty!")

        # handle singlenode need that edgenode_group has to have cplane repeated with different name
        if singlenode:
            name = list(inventory[_ansible.CPLANE_GROUP]['hosts'].keys())[0]

            ansible_host = copy.deepcopy(inventory[_ansible.CPLANE_GROUP]['hosts'][name])
            name += "_edgenode"

            inventory[_ansible.EDGENODE_GROUP] = {"hosts": {name: ansible_host}}

        file_path = os.path.join(cluster_path, "inventory.yaml")
        seo.yaml.save(inventory, file_path)

def check_config_data(cfg):
    """Checks config data for general correctness"""

    _check_duplicates(cfg)
    _check_links(cfg)

def add_default_settings(cfg):
    """Sets default values to optional configurations.

    Currently only default accounts are added by this function.
    """

    _add_default_accounts(cfg)

def _find_duplicates(names_list):
    return [n for n, c in collections.Counter(names_list).items() if c > 1]

def _check_list_duplicates(element_name, items, accessor):
    names = list(map(accessor, items))
    dups = _find_duplicates(names)

    if dups:
        dups = [f"'{d}'" for d in dups]
        raise iut.error.IutError(
            seo.error.Codes.CONFIG_ERROR,
            "IUT-X",
            f"Duplicate names {', '.join(dups)} for '{element_name}' items in platform configuration file")


def _check_duplicates(cfg):
    fields = ['accounts', 'experience_kits', 'clusters', 'configurations']

    for field in fields:
        _check_list_duplicates(field, cfg.get(field, []), lambda a: a['name'])

    # check for duplicate hosts
    bmcs = []
    addresses = []
    for c in cfg['clusters']:
        for _,hosts in c['hosts'].items():
            for host in hosts:
                if 'bmc' in host:
                    bmcs.append(host['bmc']['address'])
                if 'address' in host:
                    addresses.append(host['address'])

    dups = _find_duplicates(addresses)
    if dups:
        dups = [f"'{d}'" for d in dups]
        raise iut.error.IutError(
            seo.error.Codes.CONFIG_ERROR,
            "IUT-X",
            f"Duplicate addresses {', '.join(dups)} of hosts in platform configuration file")

    dups = _find_duplicates(bmcs)
    if dups:
        dups = [f"'{d}'" for d in dups]
        raise iut.error.IutError(
            seo.error.Codes.CONFIG_ERROR,
            "IUT-X",
            f"Duplicate addresses {', '.join(dups)} of hosts BMC's in platform configuration file")


def _check_link(items_name, items, name):
    if not any(name == n['name'] for n in items):
        raise iut.error.IutError(
            seo.error.Codes.CONFIG_ERROR,
            "IUT-X",
            f"The '{items_name}' named '{name}' does not exist in platform configuration")


def _check_links(cfg):
    """Check if the links in cfg are leading to existing elements"""

    for cluster in cfg['clusters']:
        _check_link('account', cfg['accounts'], cluster['account'])
        _check_link("configuration", cfg['experience_kits'], cluster['experience_kit']['name'])

        if 'configuration' in cluster:
            _check_link('configuration', cfg['configurations'], cluster['configuration'])


def _add_default_accounts(cfg):

    if 'accounts' not in cfg:
        logging.warning("Smart Edge Platform config had no accounts defined, adding default named 'smartedge'")
        cfg['accounts'] = [{"name": "smartedge", "username": "smartedge"}]

    for cluster in cfg['clusters']:
        if 'account' not in cluster:
            logging.warning("Cluster %s has no account specified, using first one: %s",
                cluster['name'], cfg['accounts'][0]['name'])
            cluster['account'] = cfg['accounts'][0]['name']


def generate_deployment_configuration(toolchain_cfg, platform_cfg):
    """ Generates complete configuration for ansible. """

    # something like hardcoding the path, only repo root + *single* experience kit path is supported
    root = toolchain_cfg["path"]["full"]["repo"]
    experience_kit_path = os.path.join(root, platform_cfg["experience_kits"][0]["path"])

    dst = os.path.join(experience_kit_path, "inventory/automated")

    generate_ansible_configuration(platform_cfg, experience_kit_path, dst)


    # call controller ip patch for virgo
    if toolchain_cfg['product'].get('codename') == 'virgo':
        controller_address = None
        for cluster in platform_cfg["clusters"]:
            if cluster.get("experience_kit", {}).get("deployment") == "controller":
                controller_address = cluster['hosts'][_ansible.CPLANE_GROUP][0]['address']

        if controller_address is None:
            raise iut.error.IutError(
                iut.error.Codes.RUNTIME_ERROR,
                "IUT-X",
                "Cannot determine controller IP address (no controller deployemnt found)")

        for cluster in platform_cfg["clusters"]:
            if cluster.get("experience_kit", {}).get("deployment") == "node":
                set_controller_ip(cluster['name'], controller_address, dst)


def set_controller_ip(cluster_name, controller_address, dst):
    """ Update given cluster configuration with specified controller address """

    path = os.path.join(dst, cluster_name, "group_vars/all/90-settings.yaml")

    try:
        logging.info("Patching virgo configuration to set controller IP address")
        data = seo.yaml.load(path) # nosec - B506 (project specific wrapper, safe_load used internally)

        data['se_controller']['address'] = controller_address

        seo.yaml.save(data, path)
    except Exception as e: # TODO: This is lazy programming. Basically try catch all. Bad stuff.
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR,
            "IUT-X",
            f"Cannot set controller IP address in {path} ") from e


def copy_ssh_keys_to_hosts(cfg):
    """Copies default ssh public key to all hosts defined in cfg with sshpass and ssh-copy-id"""

    # @fixme handle the situation when there is no key generated
    ssh_dir = os.path.expanduser("~/.ssh")
    if not os.path.isdir(ssh_dir):
        logging.warning("Creating ~/.ssh directory")

        os.mkdir(os.path.expanduser(ssh_dir))

    if not os.path.isfile(os.path.join(ssh_dir, "id_rsa.pub")) or not os.path.isfile(os.path.join(ssh_dir, "id_rsa")):
        logging.info("Generating ssh keys")

        path = os.path.join(ssh_dir, "id_rsa")

        cmd = ['ssh-keygen', '-f', path, '-P', '']
        logging.debug("Executing %s", str(cmd))
        subprocess.run(cmd, check=True) # nosec - B603 (subprocess call)

    known_hosts_path = os.path.expanduser('~/.ssh/known_hosts')

    for cluster in cfg['clusters']:
        account = next((a for a in cfg['accounts'] if a['name'] == cluster['account']))

        for hosts in cluster['hosts'].values():
            for host in hosts:
                target = f"{account['username']}@{host['address']}"

                # development workaround

                if os.path.isfile(known_hosts_path):
                    # just remove any existing key
                    cmd = ['ssh-keygen', '-f', known_hosts_path, '-R', host['address']]
                    logging.debug("Executing %s", str(cmd))
                    subprocess.run(cmd, check=True) # nosec - B603 (subprocess call)

                # copy the key eventually
                cmd = ['sshpass', '-p', account['password'], 'ssh-copy-id', '-o', 'StrictHostKeyChecking=no', target]
                logging.debug("Executing %s", str(cmd))
                subprocess.run(cmd, check=True) # nosec - B603 (subprocess call)


def get_git_credentials(platform_cfg, cli_args):
    """ Determine the credentials to be used when interacting with git

        Both the password and the username are processed independently, and the ones specified through the command line
        have precedence over the ones found in the platform config.

        Returns:
            Dictionary with 'username' and 'password' keys. If any of the variables doesn't occur in both data sources,
            it defaults to an empty string.

        Parameters:
            platform_cfg - platform configuration loaded from the user provided configuration file
            cli_args - parsed command line arguments object as returned by the parse_args function
    """

    creds = {
        "username": platform_cfg.get("git", {}).get("username", ""),
        "password": platform_cfg.get("git", {}).get("password", "")
    }

    if cli_args.git_user:
        creds["username"] = cli_args.git_user
    if cli_args.git_password:
        creds["password"] = cli_args.git_password

    return creds
