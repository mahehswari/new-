# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
SE Install and Upgrade Toolchain: Offline installation package building script
"""

import argparse
import copy
import logging
import os
import shutil
import tempfile

import iut.slo.deps

import iut.build
import iut.checksum
import iut.config
import iut.dir
import iut.ek
import iut.error
import iut.metadata
import iut.monitoring
import iut.run
import iut.services
import iut.shell


def parse_args(package_root, toolchain_cfg):
    """ Parse script arguments """
    product_name = toolchain_cfg["product"]["name"]

    p = argparse.ArgumentParser(
        add_help=False,
        description=f"""
            Build the {product_name} offline installation package according to the configuration
            provided
            """)

    g = p.add_argument_group("build arguments")

    g.add_argument(
        "-o", "--output", action="store", dest="output_path", metavar="PATH", required=True,
        help=f"""
            PATH to the output directory in which the build tool will create the installation package; the tool will
            create the directory which it expects not to exist; use the {iut.config.FORCE_OPT} option to delete an
            existing directory before creating it again""")
    g.add_argument(
        "--deploy-only", action="store_true", dest="deploy_only_flag",
        help="""
            build a deployment-only package that can only be used to deploy the platform on top of already installed
            operating systems; it is the system operator's responsibility to install and properly configure operating
            systems on all required machines""")

    iut.config.create_common_argument_group(p, package_root)
    iut.config.create_auth_argument_group(p, toolchain_cfg)

    args = p.parse_args()
    args.prog = p.prog
    return args


def copy_config(toolchain_cfg, cli_args):
    """ Copy config file into the output path (IUP/A/9)

        Parameters:
            toolchain_cfg - install and upgrade toolchain config as provided to the main function
            cli_args - parsed command line arguments object as returned by the parse_args function
    """

    shutil.copy(
        cli_args.config_path,
        os.path.join(cli_args.output_path, toolchain_cfg["path"]["part"]["package"]["config"]))

    logging.info("Copied the platform configuration file to the package output directory")


def _regenerate_se_context(output_path, toolchain_cfg, new_toolchain_path):
    """ Regenerates se_context file with a new toolchain path
    """
    toolchain_cfg_copy = copy.deepcopy(toolchain_cfg)

    # Keys are not needed and can be removed
    for key in ["docs", "profile", "configs", "prog"]:
        del toolchain_cfg_copy[key]
    # offline_flag should be changed to true in the newly generated se_context
    toolchain_cfg_copy['context']['offline_flag'] = True

    # TODO: `repo` key will be deleted from the se_context in the scope of the task: ESS-XXXX
    if 'full' in toolchain_cfg_copy['path']:
        toolchain_cfg_copy['path']['full'] = {}

    # path/part/package and path/part/tmp keys are not needed for the offline installation package
    for key in ["package", "tmp"]:
        del toolchain_cfg_copy['path']['part'][key]

    # Set the offline documentation directory. The commands executed in the context of the installation package will
    #  refer the user to the troubleshooting documentation included this directory when displaying an error message.
    #  See the 'iut.error.format_iut_error_msg' function:
    toolchain_cfg_copy['path']['part']['docs'] = toolchain_cfg['path']['part']['package']['docs']

    # setting new paths for path/part/package
    relative_path = os.path.relpath(new_toolchain_path, output_path)
    for key, value in toolchain_cfg_copy['path']['part'].items():
        toolchain_cfg_copy['path']['part'][key] = os.path.join(relative_path, value)

    # Generate se_requirements.txt file for the offline mode (all required packages in one file)
    toolchain_cfg_copy['path']['part']['dependencies'] = toolchain_cfg['path']['part']['dependencies']
    with open(os.path.join(output_path, toolchain_cfg_copy['path']['part']['dependencies']), "w") as f:
        f.write('\n'.join(iut.slo.deps.load(toolchain_cfg)))

    toolchain_cfg_copy['path']['part']['package'] = {}
    toolchain_cfg_copy['path']['part']['package']['checksum'] = toolchain_cfg['path']['part']['package']['checksum']

    with open(os.path.join(output_path, "se_context.py"), "w", encoding="utf-8") as f:
        f.write("TOOLCHAIN_CFG = " + repr(toolchain_cfg_copy))


def copy_deployment_toolchain_wrappers(toolchain_cfg, args, build_toolchain_path):
    """ Copies deployment toolchain wrappers to the installation package (IUP/A/49)
    """

    se_files = ["se_config.py", "se_deploy.py", "se_report.py"]

    if not args.deploy_only_flag:
        se_files.append("se_install.py")

    _regenerate_se_context(args.output_path, toolchain_cfg, build_toolchain_path)

    for file_name in se_files:
        try:
            shutil.copy(
                os.path.join(toolchain_cfg["path"]["full"]["repo"], file_name),
                args.output_path)
        except OSError as e:
            raise iut.error.IutError(
                iut.error.Codes.RUNTIME_ERROR,
                "IUT-X",
                f"File cannot be copied:\n"
                f"    {e}")


def main(args, toolchain_cfg):
    """ Script entry function """

    platform_cfg = iut.config.load_platform_cfg(args.config_path, toolchain_cfg) # pylint: disable=unused-variable

    iut.dir.create_output_path(toolchain_cfg, args.output_path, force=args.force_flag)

    tmp_root = tempfile.mkdtemp(dir=args.tmp_dir_path)

    logging.info("Created a temporary storage directory: %s", tmp_root)

    iut.metadata.create_file(toolchain_cfg, args.output_path)

    iut.monitoring.build_service(toolchain_cfg)
    iut.monitoring.save_service(toolchain_cfg, args.output_path)

    # The provisioning configuration generation and the provisioning services build actions shouldn't be ran
    # when the package is built for the deployment-only scenario (the args.deploy_only_flag is set):
    if not args.deploy_only_flag:
        provisioning_cfg_path = iut.config.generate_provisioning_config(toolchain_cfg, platform_cfg, args, tmp_root)
        git_creds = iut.config.get_git_credentials(platform_cfg, args)
        iut.build.build_services(toolchain_cfg, git_creds, provisioning_cfg_path)

    copy_config(toolchain_cfg, args)

    iut.docs.build_offline_docs(args, toolchain_cfg, args.output_path, tmp_root)

    build_toolchain_path = iut.ek.copy_experience_kits(platform_cfg, args)
    logging.info("Determined new toolchain path %s", build_toolchain_path)
    copy_deployment_toolchain_wrappers(toolchain_cfg, args, build_toolchain_path)

    # Ensure that the ownership of the entire content of the output directory is consistent:
    iut.shell.set_dir_ownership(args.output_path, iut.shell.get_user_name(), iut.shell.get_user_group())

    iut.checksum.create_package_checksum_file(toolchain_cfg, args.output_path)

    iut.metadata.update_file(toolchain_cfg, args.output_path)

    iut.checksum.create_metadata_checksum_file(toolchain_cfg, args.output_path)

    if not args.deploy_only_flag:
        iut.build.remove_esp_dirs(toolchain_cfg, tmp_root)

    logging.info(
        "Successfully created an offline installation package for %s %s",
        toolchain_cfg['product']['name'], toolchain_cfg['product']['version'])

    return iut.error.Codes.NO_ERROR


def run_main(toolchain_cfg):
    """ Convenience entry function wrapper to be called from the top-most se_build.py script """

    iut.run.run(main, parse_args, toolchain_cfg)
