#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation

"""Convenience script to provision remote host via Redfish API,
   using Virtual Media image hosted on HTTP/HTTPS/NFS/SMB share"""

import os
import sys
import logging
import argparse
import time
import signal

import redfish_api # pylint: disable=import-error

# create root logger for this script
LOGGER = logging.getLogger()

# variable used to control quitting wait loop
EJECT_NOW = False

# pylint: disable=unused-argument
def eject_handler(signum, frame):
    "Handler for siguser1 signal making loop break"
    # pylint: disable=global-statement
    global EJECT_NOW
    LOGGER.info("Received signal %d, quit wait loop", signum)
    EJECT_NOW = True

# set the signal handler, so script is called as a subprocess, parent process
# has a mean of forcing this script to gracefully finish
signal.signal(signal.SIGUSR1, eject_handler)


def parse_args():
    "Parse command-line arguments"

    parser = argparse.ArgumentParser(
        description="Convenience script to provision remote host via Redfish API, "
                    "using Virtual Media image hosted on HTTP/HTTPS/NFS/SMB share",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  ./%(prog)s --ip 10.22.22.139 -u root -p rootpass "
            "--image-url http://10.102.102.192/usb/SEO_DEK_UBUNTU/uos-efi.img\n\n"))
    parser.add_argument("-v", "--verbose",
                        help="Extended verbosity",
                        required=False,
                        action="store_true",
                        default=False)
    parser.add_argument("--ip", help="MGMT IP address", required=True)
    parser.add_argument("--user", "-u", help="MGMT username", required=True)
    parser.add_argument("--password", "-p", help="MGMT password", required=True)
    parser.add_argument(
        "--proxy", help="""
            Proxy server for traffic redirection.
            This can be HTTP/HTTPS or SOCK5 proxy.
            If omitted, https_proxy environment var will be used.
        """, required=False)
    parser.add_argument("--image-url",
                        help="Image URL to be mounted at remote host as Virtual Media. "
                        "This should be EFI image, with .img extension",
                        required=True)
    parser.add_argument("--no-logfile",
                        help="Don't log to a file",
                        required=False,
                        action="store_true",
                        default=False)
    parser.add_argument("--timeout",
                        help="Timeout to wait until provisioning finishes (in minutes)",
                        required=False,
                        type=int,
                        default=25)

    return parser.parse_args()


def main():
    "Main execution function"

    args = parse_args()

    if args.no_logfile:
        redfish_api.configure_logger(debug=True)
    else:
        redfish_api.configure_logger(debug=True, logfile=os.path.splitext(os.path.basename(__file__))[0] + '.log')

    # try to access Redfish management API with proxy, if passed by user
    proxies = None
    if args.proxy:
        LOGGER.info("Connecting to %s using passed proxy %s ...", args.ip, args.proxy)
        proxies = {"https" : args.proxy}

    elif "https_proxy" in os.environ:
        LOGGER.info("Connecting to %s using environment var https_proxy %s ...", args.ip, os.environ["https_proxy"])

    else:
        LOGGER.info("Connecting to %s without proxy ...", args.ip)

    rapi = redfish_api.RedfishAPI(args.ip, args.user, args.password, proxy=proxies, verbose=args.verbose)
    if not rapi.check_connectivity():
        LOGGER.error("Redfish API is inaccessible. Please ensure IP address is correct, and correct proxy is passed.")
        sys.exit(1)

    rapi.print_system_info()

    boot_method = rapi.system_info["Boot"]["BootSourceOverrideMode"]
    if boot_method != "UEFI":
        LOGGER.error("Only boot method 'UEFI' is supported. Change your BIOS settings.")
        sys.exit(1)

    # check prerequisites and print current media info
    if rapi.check_virtual_media_support() is False:
        LOGGER.error("This iDRAC version does not support Virtual Media")
        sys.exit(1)

    # print some debug info
    LOGGER.info("--------")
    rapi.get_virtual_media_info()

    status = rapi.get_secure_boot()
    if status:
        LOGGER.info('Secure Boot is enabled. Disabling it first to allow ESP provisioning ...')
        rapi.disable_secure_boot()
        rapi.finalize_bios_settings()

        # TODO: is this reboot needed? because we will after mounting image reboot anyway!
        if rapi.reboot_required:
            # reboot and wait till changes are applied
            rapi.perform_reboot()
            job_id = rapi.get_pending_config_jobs()[0]["Id"]
            rapi.wait_for_job_finished(job_id)
            rapi.reboot_required = False

    if args.image_url.startswith("https") and rapi.idrac_attributes.get("RFS.1.IgnoreCertWarning") != "Yes":
        LOGGER.info("Disabling HTTPS certificate check for Virtual Media...")
        rapi.patch_idrac_attributes({"RFS.1.IgnoreCertWarning": "Yes"})
    else:
        LOGGER.info("HTTPS certificate check for Virtual Media is already disabled.")

    LOGGER.info("Starting remote provisioning of host %s with image %s", args.ip, args.image_url)

    # make sure image is ejected first, otherwise inserting will fail
    try:
        rapi.validate_media_status(expect_inserted=False)
    except Exception:
        rapi.eject_virtual_media()
        rapi.validate_media_status(expect_inserted=False)

    # insert remote image
    rapi.insert_virtual_media(args.image_url)
    rapi.validate_media_status(expect_inserted=True)

    # reboot into inserted image
    rapi.set_next_onetime_boot_device_virtual_media()
    rapi.perform_reboot()

    # provisioning will start here (phase 1 - uOS), which will finish with reboot if successful,
    # 25min of wait time should be enough (usually it takes around 15-20min,
    # but can depend on platform and on network bandwidth)
    LOGGER.info("Waiting for provisioning (phase 1 - uOS) to finish ...")

    time_end = time.time() + args.timeout*60
    # wait until either we reached timeout or we got signal from parent process to quit,
    # that should be sent when phase 1 is completed (successfully or with a failure)
    while not EJECT_NOW and time.time() < time_end:
        time.sleep(5)

    # we no longer need to keep image mounted
    rapi.eject_virtual_media()
    rapi.validate_media_status(expect_inserted=False)

    # quit script
    LOGGER.info("--------")
    LOGGER.info("All actions finished successfully")
    sys.exit(0)


if __name__ == '__main__':
    main()
