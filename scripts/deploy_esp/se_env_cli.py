# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Utility command used to ensure that provisioning host environment prerequisites are fulfilled
"""

import argparse
import logging
import os
import subprocess # nosec - B404 (security implications considered)

import iut.slo.error
import iut.slo.run
import iut.slo.config


_CMD_INSTALL="install"
_CMD_VERIFY="verify"


def parse_args(package_root, toolchain_cfg): # pylint:disable=unused-argument
    """ Parse script arguments """

    product_name = toolchain_cfg["product"]["name"]

    p = argparse.ArgumentParser(
        add_help=False,
        description=f"""
            Ensure that the {product_name} provisioning system prerequisites are fulfilled
        """)

    g = p.add_argument_group("common arguments")
    iut.slo.config.add_debug_argument(g)
    iut.slo.config.add_help_argument(g)

    sp = p.add_subparsers(required=True, title="supported commands", dest="command", metavar="COMMAND")

    ic = sp.add_parser(_CMD_INSTALL, help="install and configure the provisioning system prerequisites")
    ic.add_argument(
        "-r", "--registry-mirror", action="append", metavar="URL", dest="secure_registries",
        help="""
            Secure container registry mirror URL to be used when pulling images to the provisioning host
            """)
    ic.add_argument(
        "-R", "--insecure-registry", action="append", metavar="LOCATION", dest="insecure_registries",
        help="""
            Insecure container registry URL to be used when pulling images to the provisioning host
            """)

    sp.add_parser(_CMD_VERIFY, help="check if the provisioning system prerequisites are working as expected")

    args = p.parse_args()
    args.prog = p.prog
    return args


def log_proxy_env():
    """ Log the proxy related environment variables for diagnostic purposes """
    proxy_vars_found = [v for v in ["http_proxy", "https_proxy", "ftp_proxy", "no_proxy"] if v in os.environ]

    if proxy_vars_found:
        logging.info(
            "Proxy configuration variables found in the environment:\n"
            "    %s", "\n    ".join([f'{v} = {os.getenv(v)}' for v in proxy_vars_found]))
    else:
        logging.debug("No proxy configuration variables found in the environment")


def configure_env_install(cli_args, toolchain_cfg):
    """ Configure the provisioning system prerequisites installation and configuration script.

        * Generate the <dek>/inventory/default/group_vars/admin_machine_group/20-iut-auto.yml file
        * Update the <dek>/inventory.yml file
    """

    log_proxy_env()

    def __sqs(val):
        """ Quote the value for the single quoted scalar """
        return val.replace("'", "''")

    def __fmt_var(name):
        """ Format environment variable YAML property """
        val = __sqs(os.getenv(name, ""))
        return f"{name}: '{val}'"

    amg_vars = [
        "_registry_ip_address: 'localhost'",
        "proxy_env:",
        f"  {__fmt_var('http_proxy')}",
        f"  {__fmt_var('https_proxy')}",
        f"  {__fmt_var('ftp_proxy')}",
        f"  {__fmt_var('no_proxy')}"]

    if cli_args.secure_registries:
        amg_vars.append("docker_registry_mirrors:")
        amg_vars += [f"  - '{__sqs(m)}'" for m in cli_args.secure_registries]

    if cli_args.insecure_registries:
        amg_vars.append("docker_insecure_registries:")
        amg_vars += [f"  - '{__sqs(m)}'" for m in cli_args.insecure_registries]

    out_file = os.path.join(
        toolchain_cfg["path"]["full"]["primary_ek"],
        "inventory/default/group_vars/admin_machine_group/20-iut-auto.yml")

    os.makedirs(os.path.dirname(out_file), exist_ok=True)

    with open(out_file, "w") as f:
        f.write('\n'.join(amg_vars))


## Docker registry mirrors
## https://docs.docker.com/registry/recipes/mirror/
# docker_registry_mirrors:
#   - "https://docker-mirror.example.local"


def run_env_install(toolchain_cfg):
    """ Execute the provisioning system prerequisites installation and configuration script provided by DEK """

    logging.debug("Running the automated provisioning system prerequisites installation and configuration")

    cmd = [os.path.join(toolchain_cfg["path"]["full"]["primary_ek"], "deploy.sh"), "--stage-0"]

    try:
        subprocess.run(cmd, check=True) # nosec - B603 (the user is the system administrator)
    except subprocess.CalledProcessError as e:
        logging.debug(
            "The following command has failed:\n"
            "    %s", subprocess.list2cmdline(iut.slo.system.clear_password(cmd)))

        raise iut.slo.error.IutError(
            iut.slo.error.Codes.RUNTIME_ERROR, "IUT-X",
            "Failed to install provisioning system prerequisites") from e

    logging.info("The provisioning system prerequisites were successfully installed and configured")


def main(cli_args, toolchain_cfg):
    """ Script entry function """

    if cli_args.command == _CMD_INSTALL:
        configure_env_install(cli_args, toolchain_cfg)
        run_env_install(toolchain_cfg)

    return iut.slo.error.Codes.NO_ERROR


def run_main(toolchain_cfg):
    """ Convenience entry function wrapper to be called from the top-most se_env.py script """
    iut.slo.run.run(main, parse_args, toolchain_cfg)
