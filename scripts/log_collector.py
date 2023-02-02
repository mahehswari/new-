#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2020-2021 Intel Corporation
"""
Log-Collector is a tool to collect all requested artifacts i.e.: log files, \
commands output reports/results, binary files, etc. \
This tool allows a user to single handed collect all information needed for \
developers or testers to analyze discovered or reported bugs as well as helps \
automated tests gather all required data for further analysis. \
"""

import argparse
import glob
import json
import logging
import os
import re
import shutil
import subprocess # nosec - B404
import sys
import tarfile
import tempfile


_FORCE_OPT = "--force"

def parse_options(args):
    """
    Function parses passed command-line options.

    Parameters:
    args (list): Runtime arguments.

    Returns:
    Namespace: Returning argparse namespace object with run-time arguments value.
    """
    parser = argparse.ArgumentParser(description="")

    input_group = parser.add_mutually_exclusive_group()

    input_group.add_argument(
        "-c", "--config", action="store", dest="config_file", metavar="FILE", default="log_collector.json",
        help="configuration FILE specifying artifacts to be collected (default: %(default)s)")

    input_group.add_argument(
        "--stdin", action="store_true", dest="stdin_flag",
        help="read the configuration specifying artifacts to be collected from the standard input")

    output_dir_opt = "--output-dir"
    output_file_opt = "--output-file"
    output_old_opt = "--out"

    output_group = parser.add_mutually_exclusive_group()

    output_group.add_argument(
        output_dir_opt, action="store", dest="output_dir_path", metavar="PATH",
        help="""
            output directory PATH to copy the collected files to; no archive file will be created if this option is
            provided
            """)

    output_group.add_argument(
        output_file_opt, action="store", dest="output_file", metavar="PATH",
        help="""
            output archive file PATH
            """)

    output_group.add_argument(
        "-o", output_old_opt, action="store", dest="out", metavar="FILE", default="Result.tar.gz",
        help=f"""
            name of the output archive (tgz) FILE to be created (default: %(default)s);
            this option is DEPRECATED and exists for backward compatibility only - prefer the {output_dir_opt} or
            {output_file_opt} option instead
            """)

    parser.add_argument(
        "-f", _FORCE_OPT, action="store_true", dest="force",
        help=f"""
            force the script to override an existing directory (specified using the {output_dir_opt} option),
            output file (specified using {output_file_opt} or {output_old_opt} options)
        """)

    parser.add_argument(
        "-t", "--tmp-dir", action="store", dest="tmp_dir", metavar="PATH", default=".",
        help="directory to create a temporary directory in (default: %(default)s)")

    level_debug = "DEBUG"
    levels = [level_debug, "INFO", "WARNING", "ERROR", "CRITICAL", "NONE"]

    parser.add_argument(
        "-l", "--log-level", action="store", dest="log_level", metavar="LEVEL",
        default=level_debug, choices=levels,
        help=f"console logging level (one of: {', '.join(levels)}; default: %(default)s)")

    return parser.parse_args(args)


def read_config_json(options):
    """
    Function reads configuration JSON file.

    Parameters:
    path (string): Path to read from.

    Returns:
    dict: Returning configuration dictionary on success, None otherwise.
    """

    if options.stdin_flag:
        logging.info("Reading the collector configuration from the standard input")

        try:
            return json.load(sys.stdin)
        except json.decoder.JSONDecodeError as e:
            logging.error(
                "Failed to parse the standard input configuration JSON:\n"
                "    %s", e)
            return None

    try:
        path = options.config_file

        logging.info("Reading the collector configuration from the file: %s", path)

        with open(path) as f:
            try:
                return json.load(f)
            except json.decoder.JSONDecodeError as e:
                logging.error(
                    "Failed to parse the configuration JSON file ('%s'):\n"
                    "    %s", path, e)
                return None
    except OSError as e:
        logging.error(
            "Failed to load the configuration file ('%s'):\n"
            "    %s", os.path.relpath(path), e)

    return None


def run_command(command, file_name):
    """
    Function runs command and save its result to file.

    Parameters:
    command(string): Command to run.
    file_name(string): Path to save results.
    """
    logging.debug("Saving command: %s to file: %s", command, file_name)
    with open(file_name, "w") as output_file:
        try:
            subprocess.run(command,
                        shell=True, # nosec - B602
                        stdout=output_file,
                        stderr=subprocess.STDOUT,
                        check=True,
                        universal_newlines=True)
        except subprocess.CalledProcessError as process_error:
            logging.error("Command \"%s\" failed with error: %s", command, process_error.output)
    logging.debug("Running command finished.")


def make_targz(archive_name, src):
    """
    Function creates tar.gz archive.

    Parameters:
    archive_name (string): Output archive name.
    src (string): Directory path that will be archived.
    """
    logging.info("Creating %s started.", archive_name)
    with tarfile.open(archive_name, "w:gz", dereference=True) as tar:
        try:
            tar.add(src, arcname=archive_name)
        except OSError as tar_file_exception:
            logging.error(
                "Adding artifacts to the archive \"%s\" failed with error: %s",
                archive_name, tar_file_exception)
    logging.info("Creating %s succeeded.", archive_name)


def handle_output_path(options, path, kind):
    """ Check if the path exists. Do not do anything if it doesn't. Try to remove it if --force argument was provided.
        Log an error and finish the application if the path exists but no --force argument was provided

        Parameters:
            options - parsed CLI arguments (argparse.Namespace)
            path - the path to be checked
            kind - short path type description to be used in user messages - typically 'file' or 'directory'
    """

    file_name = os.path.basename(path)
    file_dir_path = os.path.dirname(path)

    if kind == "file" and file_name != "Result.tar.gz":
        if not os.path.exists(file_dir_path) and file_dir_path != "":
            logging.error(
                "The output %s path ('%s') does not exists\n"
                "    Choose a different %s path", kind, file_dir_path, kind)
            return False

    if os.path.exists(path):
        if not options.force:
            logging.error(
                "The output %s ('%s') already exists\n"
                "    Choose a different %s, remove it manually or use the %s option to remove it"
                " automatically", kind, path, kind, _FORCE_OPT)
            return False

        logging.debug("Removing the ('%s') %s", path, kind)

        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
        except OSError as e:
            logging.error(
                "Failed to remove the output %s: %s\n"
                "    %s", kind, path, e)
            return False

        logging.debug("The output %s ('%s') was removed", kind, path)
    else:
        logging.debug("The output %s ('%s') does not exist", kind, path)

    return True


def prepare_directories_tree(options, tmp_dir, sub_dirs):
    """
    Function prepares directories tree.

    Parameters:
    options (Namespace): Options Namespace object with run-time commands.
    tmp_dir (string): Temporary directory path to store collected artifacts.
    sub_dirs (list): Sub-directories created in root directory.

    Returns:
    (int): Operation performance exit code. 0 on success, -1 otherwise.
    """

    logging.info("Preparing directories tree to collect artifacts started.")

    if options.output_dir_path is not None:
        if not handle_output_path(options, options.output_dir_path, "directory"):
            return False
    elif options.output_file is not None:
        if not handle_output_path(options, options.output_file, "file"):
            return False
    elif options.out is not None:
        logging.warning(
            "DEPRECATED --out option is being used\n"
            "    Prefer the --output-dir or --output-file option instead"
            )
        if not handle_output_path(options, options.out, "file"):
            return False

    try:
        for sub in sub_dirs:
            os.makedirs(os.path.join(tmp_dir, sub), exist_ok=True)
    except OSError as e:
        logging.error(
            "Failed to create the output directories tree:\n"
            "    %s", e)
        return False

    logging.debug("Successfully created the output directories tree")

    return True


def collect_pods_logs(file_name, com):
    """
    Function collects PODs logs into logs files.

    Parameters:
    file_name (string): sub-directory prefix path.
    com (string): command to run.
    """
    logging.debug("Collecting pods logs started.")

    try:
        pods_info_req = subprocess.run("kubectl get pods -A -o wide -o json", # nosec - B607
                                        shell=True, # nosec - B602
                                        check=True,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as process_error:
        logging.error("Failed to get pods. No logs from pods fetched. Error: %s",
                      process_error.output)
    else:
        pods = json.loads(pods_info_req.stdout.decode("utf-8"))

        for pod in pods["items"]:
            pod_name = pod["metadata"]["name"]
            pod_ns = pod["metadata"]["namespace"]

            pod_cmd = com.replace("<POD>", pod_name).replace("<NAMESPACE>", pod_ns)
            pod_path = file_name.replace("<POD>", pod_name).replace("<NAMESPACE>", pod_ns)

            if "describe" in com:
                run_command(pod_cmd, pod_path)

            if "logs" in com:
                for container in pod["spec"]["containers"]:
                    command = pod_cmd.replace("<CONTAINER>", container["name"])
                    path = pod_path.replace("<CONTAINER>", container["name"])
                    run_command(command, path)

                if "initContainers" in pod["spec"]:
                    for init_container in pod["spec"]["initContainers"]:
                        command = pod_cmd.replace("<CONTAINER>", init_container["name"])
                        path = pod_path.replace("<CONTAINER>", init_container["name"])
                        run_command(command, path)

        logging.debug("Collecting pods logs finished.")

def collect_journalctl_services_logs(file_name, com):
    """
    Function collects journalctl tool services logs files.

    Parameters:
    prefix (string): sub-directory prefix path.
    com (string): command to run.
    """
    logging.debug("Collecting journalctl services logs started.")

    try:
        output = subprocess.run( # nosec - B607
            "systemctl --no-page list-unit-files --type=service --no-legend",
            shell=True, # nosec - B602
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT).stdout.decode("utf-8")
    except subprocess.CalledProcessError as process_error:
        logging.error("Failed to get services. Error: %s", process_error.output)
    else:
        services = [x.split(" ", 1)[0] for x in output.splitlines()][:-1]
        for service_name in services:
            logging.debug("Collecting service logs for: %s", service_name)
            command = re.sub("<SERVICE>", service_name, com)
            service_name = service_name.replace(".", "_").replace("-", "_").replace("@", "_")
            path = re.sub("<SERVICE>", service_name, file_name)
            run_command(command, path)
        logging.debug("Collecting journalctl services logs finished.")

def collect_command_artifacts(root_dir, os_distro, config):
    """
    Function collects configured commands running log files.

    Parameters:
    root_dir (string): Archive root directory path
    os_distro (string): Name of os distribution
    config (dict): JSON tool configuration.
    """

    logging.info("Collecting command artifacts started.")

    for sub_dir, specs in config.items():
        logging.debug("Collecting command artifacts for: %s", sub_dir)

        for com in specs.get("commands", []):
            if os_distro not in com.get("os_family", [os_distro]):
                logging.debug("Skip command \"%s\" as %s not supported", com['command'], os_distro)
                continue

            prefix = os.path.join(root_dir, sub_dir)
            file_name = os.path.join(prefix, com["file_name"])
            if "<POD>" in com["command"] or "<NAMESPACE>" in com["command"]:
                # Need to handle PODS/NAMESPACE case
                collect_pods_logs(file_name, com["command"])
            elif "<SERVICE>" in com["command"]:
                # Need to handle journalctl SERVICEs logs
                collect_journalctl_services_logs(file_name, com["command"])
            else:
                run_command(com["command"], file_name)
    logging.debug("Collecting command artifacts finished.")


def _link_files(options):
    """ Determine if symbolic links should be created in the output directory for source artifacts being regular files
    """

    return options.output_dir_path is None


def collect_path_artifacts(options, root_dir, os_distro, config):
    """
    Function collects configured path logs and directories.

    Parameters:
    root_dir (string): Archive root directory path
    os_distro (string): Name of os distribution
    config (dict): JSON tool configuration.
    """

    logging.info("Collecting path artifacts started.")

    for sub_dir, specs in config.items():
        logging.debug("Collecting path artifacts for: %s", sub_dir)

        prefix = os.path.join(root_dir, sub_dir)

        for item in specs.get("paths", []):
            if os_distro not in item.get("os_family", [os_distro]):
                logging.debug("Skip path \"%s\" as %s not supported", item['path'], os_distro)
                continue

            if os.path.isdir(item["path"]):
                collect_directory(item, prefix)
            elif "*" in item["path"]:
                output = glob.glob(item["path"])
                for i in output:
                    if _link_files(options):
                        os.symlink(i, os.path.join(prefix, os.path.basename(i)))
                    else:
                        shutil.copyfile(i, os.path.join(prefix, os.path.basename(i)))
            elif os.path.isfile(item["path"]):
                if _link_files(options):
                    os.symlink(item["path"], os.path.join(prefix, item["file_name"]))
                else:
                    shutil.copyfile(item["path"], os.path.join(prefix, item["file_name"]))
            else:
                logging.error("Failed to find requested path \"%s\"", item['path'])

    logging.debug("Collecting path artifacts finished.")


def collect_directory(src, path):
    """
    Function collects directories as packed archives.

    Parameters:
    src (dict): Source directory info dictionary.
    path (string): Archive directory path.
    """
    logging.debug("Collecting directory %s started.", src['path'])
    with tarfile.open(os.path.join(path, src["file_name"]),
                      "w:gz",
                      dereference=True) as tar:
        try:
            tar.add(src["path"], arcname=src["path"])
        except OSError as file_exception:
            logging.debug("Adding file %s failed with error: %s", src['file_name'], file_exception)
    logging.debug("Collecting directory finished.")

def get_os_distro():
    """
    Function returns Linux OS distribution
    """
    try:
        os_release_output = subprocess.run( # nosec - B607
            "cat /etc/os-release",
            shell=True, # nosec - B602
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT).stdout.decode("utf-8")
    except subprocess.CalledProcessError as process_error:
        logging.error("Failed to get os release! Error: %s", process_error.output)
        return "Undefined"
    else:
        string_search_results = re.search(r"^ID=\"?(\w+)\"?", os_release_output, re.MULTILINE)

        if string_search_results is None or len(string_search_results.groups()) != 1:
            logging.error("Failed to get os release!")
            return "Undefined"
        return string_search_results.group(1)

def main(options):
    """
    Function main for the script.

    Parameters:
    options (string): script run-time parameters.

    Returns:
    int: Operation performance exit code. 0 on success, -1 otherwise.
    """
    if options.log_level != "NONE":
        stream_logger = logging.StreamHandler(sys.stdout)
        stream_logger.setLevel(options.log_level)
        logging.getLogger().addHandler(stream_logger)

    os_distro = get_os_distro()

    logging.info("Starting %s", os.path.basename(sys.argv[0]))
    logging.debug("Reading configuration file: %s", options.config_file)

    config = read_config_json(options)
    if config is None:
        return -1

    # This directory will be created and immediately removed if the options.output_dir_path is specified. It is an
    #  imperfection with no significant consequences. Feel free to eliminate it.
    with tempfile.TemporaryDirectory(dir=options.tmp_dir) as tmp_dir:
        if options.output_dir_path is not None:
            tmp_dir = options.output_dir_path

        if not prepare_directories_tree(options, tmp_dir, config.keys()):
            return -1

        collect_command_artifacts(tmp_dir, os_distro, config)
        collect_path_artifacts(options, tmp_dir, os_distro, config)

        if options.output_dir_path is None:
            if options.output_file is not None:
                archive_file = options.output_file
            else:
                archive_file = options.out
            make_targz(archive_file, tmp_dir)

    return 0


if __name__ == "__main__":
    logging.basicConfig(filename="log_collector.log",
                        filemode="w",
                        format='%(levelname)s: %(message)s')
    logging.getLogger().setLevel(logging.DEBUG)
    sys.exit(main(parse_options(sys.argv[1:])))
