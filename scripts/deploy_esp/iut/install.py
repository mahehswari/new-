# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Functionality related to the Operating System installation triggering
"""

import glob
import logging
import os
import signal
import subprocess  # nosec - B404 (security implications considered)
import time

import netifaces  # pylint: disable=import-error

import iut.error
import iut.monitoring

# timeout for installation in minutes
INSTALL_TIMEOUT = 120

def get_own_ip(iface=None):
    """ Detects own IP address. If an interface name is supplied, use the IP address assigned to it.
        Otherwise, use whichever NIC has outside internet access by polling Google's nameservers.
        (TODO: determine if this last part should be removed altogether and the interface argument made mandatory)
    """
    if iface:
        ipv4_addresses = netifaces.ifaddresses(iface)[netifaces.AF_INET]
        if not ipv4_addresses:
            raise iut.error.IutError(
                iut.error.Codes.CONFIG_ERROR, "IUT-X",
                f"Failed to get the host IP address from provided network interface name '{iface}'")
        return ipv4_addresses[0]['addr']

    cmd = ['ip', 'route', 'get', '8.8.8.8']
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, # nosec - B603 (subprocess call)
                            universal_newlines=True, check=False)
    if proc.returncode != 0:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR, "IUT-X",
            "Failed to get the host IP address")

    # IP address is always found right after 'src' part, its position may vary
    parts = proc.stdout.splitlines()[0].split()
    for idx, part in enumerate(parts):
        if part == 'src' and idx + 1 < len(parts):
            own_ip = parts[idx + 1]
            break
    else:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR, "IUT-X",
            "Failed parsing host IP address")

    return own_ip

def start(toolchain_cfg, platform_cfg, cli_args, machines, monitoring_service):
    """ Start the operating system installation remotely

        Parameters:
            toolchain_cfg - install and upgrade toolchain config as provided to the main function
            cli_args - parsed command line arguments object as returned by the parse_args function
            machines - list of machine specifications dictionaries
            monitoring_service - monitoring service specification
    """
    if cli_args.image_url:
        image_url = cli_args.image_url
    else:
        own_ip = get_own_ip(platform_cfg.get('admin_interface'))
        profile_name = toolchain_cfg['profile']['name']
        # The protocol is set to https as some physical machines weren't able to download the image otherwise. The
        #  redfish request returned HTTP 400 and the tcpdump listening on the provisioning system machine didn't
        #  indicate any incoming request. After the protocol was updated, everything started to work. This should be
        #  further investigated to get to the root cause (the download worked on some machines):
        # See: ESS-17146, ESS-17200
        image_url = f"https://{own_ip}/usb/{profile_name}/uos-efi.img"

    # remove previous logs
    for logfile in glob.glob("redfish_virtual_media_*.log"):
        logging.info("Removing previous logfile %s", logfile)
        os.remove(logfile)

    # for each host start independent provisioning process
    procs = []
    workdir = os.path.join(toolchain_cfg['path']['full']['repo'],
                           toolchain_cfg['path']['part']['toolchain'], 'redfishapi')

    for machine in machines:
        cmd = ['python3', 'redfish_virtual_media.py', '--ip', machine['bmc']['address'],
               '--user', machine['bmc']['username'], '--password', machine['bmc']['password'],
               '--image-url', image_url, '--no-logfile', "--timeout", str(INSTALL_TIMEOUT + 1)]
        logfile = f"redfish_virtual_media_{machine['cluster_name']}_{machine['name']}.log"

        logging.info("Starting provisioning process: %s > %s", subprocess.list2cmdline(cmd), logfile)
        procs.append(
            (machine,
            # pylint: disable=consider-using-with
            subprocess.Popen( # nosec - B603 (subprocess call)
                cmd, cwd=workdir, stdout=open(logfile, 'w'),
                stderr=subprocess.STDOUT, universal_newlines=True)))

    timeout = time.time() + INSTALL_TIMEOUT * 60
    logging.info("Waiting for all hosts to be provisioned with OS ...")

    failed = False
    # time in seconds to sleep per while loop
    sleep_time = 10
    # To log one time messages different than os_end or os_fail
    one_time_log_messages = set()
    # wait and poll, until all started processes have finished, user has interrupted or timeout exceeded
    while time.time() < timeout:
        if not procs:
            break
        try:
            iut.monitoring.update_machines_status(machines, monitoring_service)
        except iut.error.IutError as iuterror:
            # Lets just print warning and hope service become available
            # if not further update will fail whole procedure anyway.
            logging.warning("Failed to update machine status.")
            logging.warning("During machine status update exception occurred: %s", iuterror)

        for machine, proc in procs[:]:
            try:
                finished = False
                # First handle possibility of error in upstream script
                if proc.poll() is not None:
                    if proc.returncode != 0:
                        logging.error("Provisioning %s process %s failed: %s", machine['name'], proc.pid, proc.args)
                        failed = True
                        finished = True
                else:
                    machine_status = machine.get("status", None)
                    if not machine_status:
                        # This is bad, but do not fail with hope of next update working properly
                        logging.warning("Failed to get status update for machine %s", machine['name'])
                    elif machine_status == "os_end":
                        logging.info("Provisioning machine %s successfully ended.", machine['name'])
                        finished = True
                    elif machine_status == "os_fail":
                        logging.error("Provisioning %s failed due to os_fail message received.", machine['name'])
                        failed = True
                        finished = True
                    else:
                        if machine_status not in one_time_log_messages:
                            logging.info("New status value '%s' received for machine %s",
                                         machine_status, machine['name'])
                            one_time_log_messages.add(machine_status)

                if finished:
                    proc.send_signal(signal.SIGUSR1)
                    procs.remove((machine, proc))

            except KeyboardInterrupt as e:
                for p in procs:
                    logging.info("Killing subprocess %s ...", p.pid)
                    p.kill()
                raise iut.error.IutError(
                    iut.error.Codes.RUNTIME_ERROR, "IUT-X",
                    "Script terminated by the user") from e
        time.sleep(sleep_time)
    else:
        logging.error("Timeout exceeded killing all left processes.")
        for machine, proc in procs:
            proc.kill()
        failed = True

    if failed:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR, "IUT-X",
            "Provisioning process failed")

    logging.info("All provisioning processes have succeeded")
