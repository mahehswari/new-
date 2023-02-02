# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation

""" Monitoring service interaction functions """

import itertools
import logging
import os
import secrets
import subprocess # nosec - B404 (security implications considered)
import time
from typing import Set
import urllib

import requests # pylint: disable=import-error

import redfishapi.redfish_api
import iut.error
import iut.seq
import iut.str

# @todo: Should be built dynamically
_SERVICE_TAG = "iut/monitoring/service:0.1"

# timeout for http requests
HTTP_TIMEOUT = 5

def build_service(toolchain_cfg):
    """ Build the monitoring service container image """

    src_path = os.path.join(
        toolchain_cfg["path"]["full"]["repo"],
        toolchain_cfg["path"]["part"]["monitoring_service"])

    cmd = ["sudo", "docker", "build", "--tag", _SERVICE_TAG, src_path]

    try:
        subprocess.run(cmd, check=True) # nosec - B603 (subprocess call)
    except subprocess.CalledProcessError as e:
        raise iut.error.IutError(
            iut.error.Codes.INTERNAL_ERROR,
            "IUT-5",
            "Failed to build the monitoring service container image\n"
            "    The following build command has failed:\n"
            f"        {subprocess.list2cmdline(cmd)}") from e


def extract_machine_list(platform_cfg):
    """ Extract list of involved machines from the provided platform configuration """
    machines = []

    for cluster in platform_cfg["clusters"]:
        for group, hosts in cluster["hosts"].items():
            for host in hosts:
                if len(host.keys()) == 1:
                    logging.debug("Host '%s' in group '%s' from cluster '%s' is a link",
                                  host['name'], group, cluster['name'])
                    continue

                host["cluster_name"] = cluster['name']
                machines.append(host)

    return machines


def retrieve_machine_data(machines):
    """ Retrieve MAC addresses of each of given machines using the Redfish API.
        This function is used only in the full provisioning scenario.

        Parameters:
            machines - list of machine specifications as provided by the extract_machine_list function
    """

    for machine in machines:
        bmc = machine.get("bmc")

        if bmc is not None:
            logging.debug("Retrieving machine (%s) network adapter information", machine["name"])
            api = redfishapi.redfish_api.RedfishAPI(bmc["address"], bmc["username"], bmc["password"])
            res = api.get_nic()
            machine["macs"] = tuple(itertools.chain.from_iterable([x["AssociatedNetworkAddresses"] for x in res]))
            logging.debug("Successfully retrieved information about %d network adapters", len(res))
        else:
            logging.info(
                "Skipping machine (%s) network adapter information retrieval as the platform configuration doesn't"
                " provide its BMC specification", machine["name"])

    return machines


def register_machines(machines: list, service: dict):
    """ Register provided machines in the monitoring service

        Parameters:
            machines - list of machine specifications as provided by the extract_machine_list and extended by the
                retrieve_machine_data functions
            service - monitoring service specification as provided by the run_service function
    """

    # Generate a list of unique, random identifiers to be assigned to machines.
    ids: Set[str] = set()

    while len(ids) < len(machines):
        ids.add(secrets.token_hex(16))

    # Register each of the machines in the monitoring service.

    for machine in machines:
        # Assign on one of the just generated identifiers to a machine
        machine["id"] = ids.pop()

        url_parts = (
            service["schema"], f"{service['addr']}:{service['port']}",
            "machines", "", "", "")
        payload = {
            "id": machine["id"],
            "status": "init"
        }

        # @todo: This will need some exception catching
        response = requests.post(urllib.parse.urlunparse(url_parts), json=payload, timeout=HTTP_TIMEOUT)

        if response.status_code != 201:
            raise iut.error.IutError(
                # @todo: Provide additional error context
                iut.error.Codes.RUNTIME_ERROR,
                "IUT-X",
                "Failed to interact with the monitoring service")

        logging.debug(
            "Successfully registered the machine (name: %s, id: %s) in the monitoring service",
            machine["name"], machine["id"])

    logging.info("Registered %d machine%s in the monitoring service", len(machines), iut.str.sgpl(machines))


def save_service(toolchain_cfg, package_path):
    """ Save the monitoring service container image to provided location """

    output_path = os.path.join(package_path, toolchain_cfg["path"]["part"]["package"]["monitoring_service"])

    cmd = ["sudo", "docker", "save", _SERVICE_TAG, "-o", output_path]

    try:
        subprocess.run(cmd, check=True) # nosec - B603 (subprocess call)
    except subprocess.CalledProcessError as e:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR,
            "IUT-X",
            "Failed to interact with docker\n"
            "    The following command has failed:\n"
            f"        {subprocess.list2cmdline(cmd)}") from e

    logging.debug("Saved the '%s' container image to the '%s' file", _SERVICE_TAG, output_path)

    cmd = ["sudo", "chmod", "go+r", output_path]

    try:
        subprocess.run(cmd, check=True) # nosec - B603 (subprocess call)
    except subprocess.CalledProcessError as e:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR,
            "IUT-X",
            "Failed to change file privileges\n"
            "    The following command has failed:\n"
            f"        {subprocess.list2cmdline(cmd)}") from e

    logging.debug("Updated the '%s' file permisions to make it readable for everyone", output_path)

    logging.info("Saved the monitoring service container image")


def stop_services():
    """ Stop the running monitoring services. Only the services matching the _SERVICE_TAG will be stopped """

    cmd = ["sudo", "docker", "ps", "--quiet", "--filter", f"ancestor={_SERVICE_TAG}"]

    try:
        proc = subprocess.run( # nosec - B603 (subprocess call)
            cmd, stdout=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as e:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR,
            "IUT-X",
            "Failed to interact with docker\n"
            "    The following command has failed:\n"
            f"        {subprocess.list2cmdline(cmd)}") from e

    # The --quiet options instruct docker to display only the container IDs, so the output parsing is only about
    # splitting lines:
    all_ids = proc.stdout.splitlines()

    logging.debug("Found %d running monitoring service instance%s", len(all_ids), iut.str.sgpl(all_ids))

    for ids in iut.seq.chop(all_ids, 32):
        cmd = ["sudo", "docker", "stop"] + ids

        try:
            subprocess.run(cmd, check=True) # nosec - B603 (subprocess call)
        except subprocess.CalledProcessError as e:
            raise iut.error.IutError(
                iut.error.Codes.RUNTIME_ERROR,
                "IUT-X",
                "Failed to interact with docker\n"
                "    The following command has failed:\n"
                f"        {subprocess.list2cmdline(cmd)}") from e

        logging.debug("Stopped a group of %d monitoring service instance%s", len(ids), iut.str.sgpl(all_ids))

    logging.info("Stopped %d monitoring service instance%s", len(all_ids), iut.str.sgpl(all_ids))

def update_machines_status(machines: list, service: dict):
    """ Updates status field in each machine representing dictionary accordingly to service information.

        Parameters:
            machines - list of machine specifications as provided by the extract_machine_list function and extended by
            the retrieve_machine_data functions.
            service - monitoring service specification as provided by the run_service function
    """
    url_parts = (
    service["schema"], f"{service['addr']}:{service['port']}", "machines", "", "", "")
    url = urllib.parse.urlunparse(url_parts)

    # Create a lookup table mapping machine id to machine object
    id_to_machine = {m["id"]: m for m in machines}

    # Register spotted alien machines to not spam the system operator with the same messages:
    known_aliens = set()
    response = requests.get(url, timeout=HTTP_TIMEOUT)

    if response.status_code != 200:
        raise iut.error.IutError(
            # @todo: Provide additional error context
            iut.error.Codes.RUNTIME_ERROR,
            "IUT-X",
            "Failed to interact with the monitoring service")

    payload = response.json()

    # Log information about status changes and update states
    for msg in payload["items"]:
        if msg["id"] not in id_to_machine:
            if msg["id"] not in known_aliens:
                logging.warning("Alien machine spotted: %s", msg["id"])
                known_aliens.add(msg["id"])
        else:
            machine = id_to_machine[msg["id"]]
            machine_status = machine.get("status", "unknown")
            if machine_status != msg["status"]:
                logging.info(
                    "A machine (%s) changed its status from %s to %s",
                    machine['name'],
                    machine_status,
                    f"'{msg['status']}'")
                machine["status"] = msg["status"]
            if 'ip' in msg:
                logging.debug('A machine %s reported its address as %s', machine['name'], msg['ip'])
                machine["address"] = msg['ip']

def sync_machines_status(machines: list, service: dict, desired_status: str):
    """ Wait for all the tracked machines to reach given status.

        Parameters:
            machines - list of machine specifications as provided by the extract_machine_list function and extended by
                the retrieve_machine_data functions
            service - monitoring service specification as provided by the run_service function
            desired_status - one of the statuses supported by the monitoring service; inspect the Status field of the
                machinePayload structure defined in the <dek>/iut/monitoring/service/handlers/machine.go file.
    """

    # @todo: The timeout could be configurable both in the toolchain config and then in the platform config:
    timeout_delta = 60 * 60 # [sec]

    logging.info(
        "Waiting for %d machine%s to reach the '%s' status (timeout: %ds)",
        len(machines), iut.str.sgpl(machines), desired_status, timeout_delta)

    timeout = time.time() + timeout_delta

    url_parts = (
        service["schema"], f"{service['addr']}:{service['port']}",
        "machines", "", "", "")
    url = urllib.parse.urlunparse(url_parts)

    # Create a lookup table mapping machine id to its specification (provided by the 'extract_machine_list' function,
    #  and extended by the 'retrieve_machine_data' function). Extend the machine specification by the 'status' field
    #  which is needed for the change detection code:
    spec_lut = {m["id"]: dict(m, status=None) for m in machines}

    # Register spotted alien machines to not spam the system operator with the same messages:
    known_aliens = set()

    # Poll the monitoring service for the services status as long as they all achieve the desired status or a timeout
    #  occurs:
    while time.time() < timeout:
        response = requests.get(url, timeout=HTTP_TIMEOUT)

        if response.status_code != 200:
            raise iut.error.IutError(
                # @todo: Provide additional error context
                iut.error.Codes.RUNTIME_ERROR,
                "IUT-X",
                "Failed to interact with the monitoring service")

        payload = response.json()

        # Log information about status changes

        for m in payload["items"]:
            if m["id"] not in spec_lut:
                if m["id"] not in known_aliens:
                    logging.warning("Alien machine spotted: %s", m["id"])
                    known_aliens.add(m["id"])
            else:
                spec = spec_lut[m["id"]]
                if spec["status"] != m["status"]:
                    logging.info(
                        "A machine (%s) changed its status from %s to %s",
                        spec["name"],
                        "unknown" if spec["status"] is None else f"'{spec['status']}'",
                        f"'{m['status']}'")
                    spec["status"] = m["status"]

        # Check if all the machines have reached the desired synchronization status:

        statuses = {s["status"] for s in spec_lut.values()}

        if (len(statuses) == 1) and (statuses.pop() == desired_status):
            logging.info("All the tracked machines have reached the '%s' status", desired_status)
            return True

        time.sleep(5)

    raise iut.error.IutError(
        iut.error.Codes.RUNTIME_ERROR,
        "IUT-X",
        f"Gave up waiting for all the machines to reach the '{desired_status}' status")

def run_service(publish_port=8080):
    """ Run the monitoring service """

    stop_services()

    # @todo: The monitoring service exposed port should be published to a random port

    cmd = ["sudo", "docker", "run", "--rm", "--detach",
           "-p", f"{publish_port}:8080/tcp",
           _SERVICE_TAG, "--log-level=info"]

    try:
        proc = subprocess.run( # nosec - B603 (subprocess call)
            cmd, stdout=subprocess.PIPE, universal_newlines=True, check=True)
    except subprocess.CalledProcessError as e:
        raise iut.error.IutError(
            iut.error.Codes.RUNTIME_ERROR,
            "IUT-5",
            "Failed to start the monitoring service\n"
            "    The following command has failed:\n"
            f"        {subprocess.list2cmdline(cmd)}") from e

    logging.info("Started the monitoring service (container id: %s)", proc.stdout.strip())

    return {
        "schema": "http",
        "addr": "localhost",
        "port": "8080",
        "container_id": proc.stdout
    }
