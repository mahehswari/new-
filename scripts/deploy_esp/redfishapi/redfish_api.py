#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2022 Intel Corporation

"Provides configuration possibilities via Redfish API"

import json
import os
import warnings
import logging
import time
import requests # pylint: disable=import-error

# urllib3 is imported dynamically by requests, get it from packages submodule
urllib3 = getattr(requests.packages, 'urllib3')

# use root logger, the same one that calling script is using
LOGGER = logging.getLogger()


class NoTpmModuleException(Exception):
    "Exception for missing TPM module in the system"
    def __str__(self):
        return "No 'TpmSecurity' found in system bios attributes. " \
               "Please ensure TPM module is installed in the system."


def configure_logger(debug: bool, logfile: str = None):
    "Configure logger"

    if debug:
        level = logging.DEBUG
    else:
        level = logging.INFO
    LOGGER.setLevel(level)

    # stdout handler
    handler = logging.StreamHandler()
    if debug:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s | %(name)s | %(message)s", "%H:%M:%S"))
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s | %(message)s", "%H:%M:%S"))
    handler.setLevel(level)
    LOGGER.addHandler(handler)

    if logfile:
        # log file handler (always remove previous logs of this script)
        if os.path.exists(logfile):
            os.remove(logfile)
        handler = logging.FileHandler(logfile)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s | %(name)s | %(message)s", "%H:%M:%S"))
        handler.setLevel(level)
        LOGGER.addHandler(handler)

    # configure underlying loggers
    if debug:
        logging.getLogger("requests").setLevel(level)
        logging.getLogger("urllib3").setLevel(level)

    # ignore warnings coming from underlying modules
    warnings.filterwarnings("ignore")


class RedfishAPI:
    "Redfish management REST API wrapper"

    # pylint: disable=too-many-instance-attributes, too-many-public-methods
    # The current number is reasonable

    # How many seconds to wait for the server to send data before giving up
    #  Increased from 10 to 90:
    #  * The timeout occurred when the installation media couldn't be downloaded by the target machine and was covering
    #    the true error response. See: ESS-17200
    HTTP_RESPONSE_TIMEOUT = 90

    def __init__(self, address, username, password, proxy=None, verbose=False):
        self.address = address
        self.username = username
        self.password = password
        # Note: when proxy is None, env variable https_proxy is read by 'requests' module
        self.proxy = proxy
        self.verbose = verbose
        # System ID and Manager ID acquired, vary depending on platform
        self._system_id = None
        self._manager_id = None
        # BIOS attributes to be applied
        self._pending_bios_attributes = {}
        # For enabling SGX a number of BIOS attributes must be applied in given sequence
        self._pending_bios_attributes_stages = []
        # Current acquired BIOS attributes
        self._bios_attributes = {}
        # currently acquired idrac settings attributes
        self._idrac_attributes = {}
        # Hint that reboot is needed in order for config job to complete
        self.reboot_required = False
        # All REST calls use single session object
        self._session = requests.Session()
        self._session.auth = (username, password)

    def _request(self, method: str, endpoint: str, check=True, timeout=HTTP_RESPONSE_TIMEOUT, **kwargs):
        """Generic HTTP request.

        Args:
            method: name of REST method available in requests library. Possible values: get, post, put, patch, delete.
            endpoint: path to be appended to URL. If it is missing /redfish/v1 prefix, then prefix will also be added.
            check: to check response and raise exception in case of bad status code.
            kwargs: additional named parameters to pass for HTTP request.
        Returns:
            requests.Response: received Response object.
        """
        def print_extended_info(response):
            # some calls have valid empty responses
            if response.text:
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    LOGGER.error("Malformed JSON received. Data: %s", response.text)
                    return

                try:
                    LOGGER.info("Extended Info Message: %s\n", json.dumps(data, indent=2))
                except Exception as e:
                    LOGGER.error("Can't decode extended info message. Exception: %s", e)

        def check_response(response):
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                LOGGER.error("Request returned incorrect response code: %s", e)
                print_extended_info(response)
                raise e

        # by default we expect json data in POST and PATCH
        if "headers" not in kwargs and method in ("post", "patch"):
            kwargs["headers"] = {"content-type": "application/json"}

        # convert dict to json string
        if "data" in kwargs:
            kwargs["data"] = json.dumps(kwargs["data"])

        # support case where user provided full Redfish path
        if endpoint.startswith('/redfish'):
            url = f"https://{self.address}{endpoint}"
        else:
            url = f"https://{self.address}/redfish/v1{endpoint}"

        # disable the InsecureRequestWarning explicitly, as per https://github.com/psf/requests/issues/2214,
        # the "verify=False" parameter is not supposed to suppress the warning
        with warnings.catch_warnings():
            warnings.filterwarnings(action='ignore', category=urllib3.exceptions.InsecureRequestWarning)

            # get HTTP method attribute by name and calls it
            response = getattr(self._session, method)(
                url,
                verify=False,  # nosec
                proxies=self.proxy,
                timeout=timeout,
                **kwargs)

        if check:
            check_response(response)

        if self.verbose:
            print_extended_info(response)

        return response

    def check_connectivity(self, endpoint="", error_passthrough=False):
        "Check if base URL is accessible for further operations"
        try:
            self._request("get", endpoint, timeout=10)
        except requests.exceptions.RequestException as e:
            LOGGER.error("check_connectivity() failed: %s", e)
            if error_passthrough:
                raise e
            return False
        return True

    ###### BASIC OPERATIONS ######

    @property
    def system_id(self) -> str:
        """Returns id of first system managed by interface.

        Note:
            Assumes there will be only single member.
            Returned system_id can vary depending on platform.
        """
        if not self._system_id:
            response = self._request("get", "/Systems")
            self._system_id = str(response.json()["Members"][0]["@odata.id"]).replace("/redfish/v1/Systems/", "")
        return self._system_id

    @property
    def manager_id(self) -> str:
        """Returns id of first manager.

        Note:
            Assumes there will be only single member.
            Returned manager_id can vary depending on platform.
        """
        if not self._manager_id:
            response = self._request("get", "/Managers")
            self._manager_id = str(response.json()["Members"][0]["@odata.id"]).replace("/redfish/v1/Managers/", "")
        return self._manager_id

    @property
    def system_info(self) -> dict:
        "Returns dictionary with ComputerSystem schema attributes"
        response = self._request("get", f"/Systems/{self.system_id}")
        return response.json()

    @property
    def manager_info(self) -> dict:
        "Returns dictionary with Manager schema attributes"
        response = self._request("get", f"/Managers/{self.manager_id}")
        return response.json()

    @property
    def is_trenton(self) -> bool:
        "Checks if system is Trenton"
        return self.system_id == "123456789abcdef"

    @property
    def is_supermicro(self) -> bool:
        "Checks if system is Supermicro"
        return self.system_id == "1"

    @property
    def is_dell(self) -> bool:
        "Checks if system is Dell"
        return self.system_id == "System.Embedded.1"

    @property
    def bios_attributes(self) -> dict:
        """Returns dictionary with current bios attributes.
           To lower redundant GET requests, attributes are cached.
        """
        if not self._bios_attributes:
            self.get_bios_attributes()
        return self._bios_attributes

    def get_bios_attributes(self):
        "Reacquire current bios attributes"
        response = self._request("get", f"/Systems/{self.system_id}/Bios")
        self._bios_attributes = response.json()["Attributes"]

    @property
    def idrac_attributes(self) -> dict:
        """Returns dictionary with current idrac manager attributes.
           To lower redundant GET requests, attributes are cached.
        """
        if not self._idrac_attributes:
            self.get_idrac_attributes()
        return self._idrac_attributes

    def get_idrac_attributes(self):
        "Reacquire current idrac manager attributes"
        response = self._request("get", f"/Managers/{self.manager_id}/Attributes")
        self._idrac_attributes = response.json()["Attributes"]

    def set_bios_attributes(self, bios_attributes: dict):
        """Sets pending attributes dictionary.
           For changes to be applied finalize_bios_settings() should be called.
        """
        self._pending_bios_attributes = {}
        self._pending_bios_attributes.update(bios_attributes)

    def print_system_info(self):
        "Print info about remote system"
        boot_method = self.system_info["Boot"]["BootSourceOverrideMode"]
        LOGGER.info("Detected HW system: %s, %s", self.system_info["Model"], self.system_info["Manufacturer"])
        LOGGER.info("Detected iDRAC version: %s", self.manager_info["FirmwareVersion"])
        LOGGER.info("Detected BIOS version: %s", self.system_info["BiosVersion"])
        LOGGER.info("Detected boot method: %s", boot_method)
        LOGGER.info("Retrieved system id: %s", self.system_id)
        LOGGER.info("Retrieved manager id: %s", self.manager_id)

    def enable_secure_boot(self):
        "Enable Secure Boot feature"
        self._pending_bios_attributes["SecureBoot"] = "Enabled"

    def disable_secure_boot(self):
        "Disable Secure Boot feature"
        self._pending_bios_attributes["SecureBoot"] = "Disabled"

    def get_secure_boot(self) -> bool:
        "Returns bool value representing status of Secure Boot feature"
        return self.bios_attributes["SecureBoot"] == "Enabled"

    def enable_tpm(self):
        "Enable TPM feature"
        self._pending_bios_attributes["TpmSecurity"] = "On"

    def disable_tpm(self):
        "Disable TPM feature"
        self._pending_bios_attributes["TpmSecurity"] = "Off"

    def get_tpm(self) -> bool:
        "Returns bool value representing status of TPM feature"

        if "TpmSecurity" not in self.bios_attributes:
            raise NoTpmModuleException
        return self.bios_attributes["TpmSecurity"] == "On"

    def enable_sgx(self):
        "Enable Intel SGX feature"
        self._pending_bios_attributes_stages = \
            [{"MemOpMode": "OptimizerMode", "NodeInterleave": "Disabled"},
             {"MemoryEncryption": "SingleKey"},
             {"IntelSgx": "On", "SgxFactoryReset": "On"},
             {"PrmrrSize": "64G"}]

    def disable_sgx(self):
        "Disable Intel SGX feature"
        self._pending_bios_attributes["IntelSgx"] = "Off"

    def get_sgx(self) -> bool:
        "Returns bool value representing status of Intel SGX feature"
        return self.bios_attributes["IntelSgx"] == "On"

    def get_nic(self) -> list:
        """Returns list of dictionaries representing system network interfaces

        To get detailed information following GET /redfish/v1/Chassis/System.Embedded.1 request chain is done:
            /NetworkAdapters - for Members field - array listing network devices endpoints.
            /NetworkAdapters/NIC.Embedded.1 - example member endpoint from which we get
            'Links'.'NetworkPorts' array for listing endpoints for actual NIC ports.
            /NetworkAdapters/NIC.Embedded.1/NetworkDeviceFunctions/NIC.Embedded.1-1-1 - example port
            from 'NetworkPorts' array that gives json data for output.
        """
        request = self._request("get", f"/Chassis/{self.system_id}/NetworkAdapters")
        # modifies [{"@odata.id": enpoint}, ...] -> [endpoint, ...]
        nic_list = (tuple(m.values())[0] for m in request.json().get("Members", []))
        output = []
        for nic_endpoint in nic_list:
            response = self._request("get", nic_endpoint, check=False)
            if response.status_code == 404:
                # on some machines endpoint 'NIC.Slot' is listed in network adapters
                # but does not really exist when we get its details, so skip over such interfaces
                LOGGER.debug("NIC endpoint %s does not exist. Skipping.", nic_endpoint)
                continue
            controllers = response.json().get("Controllers", [])
            if not controllers:
                return []
            ports = controllers[0].get("Links", {}).get("NetworkPorts", [])
            ports = (tuple(p.values())[0] for p in ports)
            output.extend([self._request("get", p).json() for p in ports])
        return output


    ###### CONFIG JOBS ######

    def create_config_job(self) -> requests.Response:
        "Creates bios config job for Dell iDRAC (for applying changes added to /Bios/Settings endpoint)"

        LOGGER.info("Creating config job.")

        payload = {"TargetSettingsURI": f"/redfish/v1/Systems/{self.system_id}/Bios/Settings"}
        return self._request("post",
                             f"/Managers/{self.manager_id}/Jobs",
                             data=payload)

    def get_pending_config_jobs(self, job_type="BIOSConfiguration") -> list:
        "Returns list of jobs of given type that are marked as 'Scheduled'"
        response = self._request("get", f"/Managers/{self.manager_id}/Jobs?$expand=*($levels=1)")
        return [job  for job in response.json()["Members"]
                if job["JobState"] == "Scheduled" and job["JobType"] == job_type]

    def delete_pending_config_jobs(self):
        "Deletes pending config jobs"
        for job in self.get_pending_config_jobs():
            LOGGER.info("Deleting job: %s", job['Id'])
            self._request("delete", f"/Managers/{self.manager_id}/Jobs/{job['Id']}")

    def get_job_info(self, job_id: str) -> dict:
        "Returns job data"
        response = self._request("get", f"/Managers/{self.manager_id}/Jobs/{job_id}")
        return response.json()

    def wait_for_job_finished(self, job_id: str, timeout=1800, check_every=12):
        """Waits for job with specific id to be finished.

        Args:
            job_id: Job ID
            timeout: Total time to wait until system is in desired power state (in seconds).
            check_every: Time between checks (in seconds).
        """

        LOGGER.info("Waiting for job %s to finish ...", job_id)

        prev_percentage = None
        for _ in range(timeout//check_every):
            job_data = self.get_job_info(job_id)

            if "PercentComplete" in job_data and job_data["PercentComplete"] != prev_percentage:
                prev_percentage = job_data["PercentComplete"]
                LOGGER.info("Job %s completion is %s percent.", job_id, prev_percentage)

            time.sleep(check_every)

            job_state = job_data["JobState"]
            if job_state in ["Scheduled", "Running", "New", "Scheduling", "ReadyForExecution", "Waiting"]:
                continue

            if job_state in ["Failed", "CompletedWithErrors", "RebootFailed"]:
                msg = ["Job did not succeeded.",
                       "Job details:"] + [f"{k}: {v}" for k, v in job_data.items()]
                raise Exception("\n\t".join(msg))

            if job_state == "Completed":
                LOGGER.info("Job %s completed.", job_id)
                break
        else:
            msg = ["Job did not succeeded within given interval.",
                   f"JobState {job_state}",
                   "Job details:"] + [f"{k}: {v}" for k, v in job_data.items()]
            raise Exception("\n\t".join(msg))

    ###### CHANGING BIOS ATTRIBUTES ######

    def apply_pending_bios_attributes(self):
        "From pending changes BIOS attributes, remove those that are already applied"

        # check if configuration is not already satisfied
        current = self.bios_attributes
        for key, val in self._pending_bios_attributes.copy().items():
            if key in current and current[key] == val:
                del self._pending_bios_attributes[key]

    def get_pending_bios_attributes_stages(self):
        "Get pending BIOS attributes and stages"

        # if SGX stages are necessary, merge them with rest of BIOS attributes,
        # so they are all applied with minimum number of reboots
        if self._pending_bios_attributes_stages:
            stages = self._pending_bios_attributes_stages.copy()
            stages[0].update(self._pending_bios_attributes)
        else:
            stages = [self._pending_bios_attributes]

        pending_attrs = {}
        pending_stages = []

        # filter out attributes and stages that are already applied
        current = self.bios_attributes
        for stage in stages:
            s = {}
            for key, val in stage.items():
                if key not in current or current[key] != val:
                    pending_attrs[key] = val
                    s[key] = val
            if s:
                pending_stages.append(s)

        return pending_attrs, pending_stages

    def patch_bios_settings(self, payload_data: dict):
        """Sends PATCH REST request to /Bios/Settings endpoint.

        Args:
            payload_data: data to be send as json.
        Returns:
            requests.Response: received Response object.
        """

        LOGGER.debug("Patching bios attributes: %s", payload_data["Attributes"])

        return self._request("patch",
                             f"/Systems/{self.system_id}/Bios/Settings",
                             data=payload_data)

    def finalize_bios_settings(self):
        """Finalizes changes to BIOS configuration
           (on Dell machines changing BIOS settings require creation of config job to take effect)
        """

        # Filter out settings that are already satisfied
        self.apply_pending_bios_attributes()

        # Return if no change in settings
        if not self._pending_bios_attributes:
            return

        # Delete pending config jobs as there can be only single config job
        self.delete_pending_config_jobs()

        # Update only differing settings
        self.patch_bios_settings({"Attributes": self._pending_bios_attributes})

        # Create config job
        self.create_config_job()
        # Clear pending attributes and hint that reboot is needed in order for config job to complete
        self._pending_bios_attributes = {}
        self.reboot_required = True

    ###### POWER CYCLING ######

    def system_reset_action(self, reset_type: str):
        """Resets system.

        Args:
            reset_type: one of [On, ForceOff, ForceRestart, GracefulShutdown, PushPowerButton, Nmi]
        """
        endpoint = f"/Systems/{self.system_id}/Actions/ComputerSystem.Reset"
        payload = {"ResetType": reset_type}
        return self._request("post", endpoint, data=payload)

    def wait_for_power_state(self, power_state: str, timeout=60, check_every=2):
        """Waits for system power state change.

        Args:
            power_state: Desired power state - string, one of [On, Off]
            timeout: Total time to wait until system is in desired power state (in seconds).
            check_every: Time between checks (in seconds).
        """
        for _ in range(timeout//check_every):
            # sometimes call may fail with status code 500, so must catch the exception and continue
            try:
                if self.system_info["PowerState"] == power_state:
                    return True
            except Exception as e:
                LOGGER.error("Error while waiting for power state change: %s", e)
            time.sleep(check_every)
        return False

    def system_shutdown(self):
        "Shutdown system"

        LOGGER.info("Setting PowerState: GracefulShutdown")
        self.system_reset_action("GracefulShutdown")

        LOGGER.info("Waiting for PowerState: Off ...")
        if not self.wait_for_power_state("Off"):
            LOGGER.warning("System did not gracefully shutdown within time limit. Trying with PowerState: ForceOff ...")
            self.system_reset_action("ForceOff")

            LOGGER.info("Waiting for PowerState: Off ...")
            if not self.wait_for_power_state("Off"):
                raise Exception("System did not forcefully shutdown within time limit")

        LOGGER.info("System is PowerState: Off")

    def system_start(self):
        "Start system"

        LOGGER.info("Setting PowerState: On")
        self.system_reset_action("On")

        LOGGER.info("Waiting for PowerState: On ...")
        if not self.wait_for_power_state("On"):
            raise Exception("System did not started within time limit")

    def perform_shutdown(self):
        "Shutdown system"

        power_state = self.system_info["PowerState"]
        LOGGER.info("Current PowerState is: %s", power_state)

        if power_state == "Off":
            LOGGER.info("System is already shutdown")
        else:
            LOGGER.info("Shutting down ...")
            self.system_shutdown()

    def perform_reboot(self):
        "Reboots system"

        power_state = self.system_info["PowerState"]
        LOGGER.info("Current PowerState is: %s", power_state)
        LOGGER.info("Rebooting ...")

        if power_state == "On":
            self.system_shutdown()

        self.system_start()

        LOGGER.info("Rebooting completed.")

    ###### VIRTUAL MEDIA ######

    def check_virtual_media_support(self):
        "Checks if Virtual Media is supported on this iDRAC version"
        endpoint = f"/Managers/{self.manager_id}/VirtualMedia/CD"
        response = self._request("get", endpoint)
        data = response.json()

        if 'Actions' in data:
            for i in data['Actions']:
                if i in ("#VirtualMedia.InsertMedia", "#VirtualMedia.EjectMedia"):
                    return True
        return False

    def get_virtual_media_info(self):
        "Prints info about Virtual Media"
        endpoint = f"/Managers/{self.manager_id}/VirtualMedia"
        response = self._request("get", endpoint)
        data = response.json()

        virtual_media_uris = [media_uri  for i in data['Members']  for media_uri in i.values()]

        for uri in virtual_media_uris:
            LOGGER.debug("Detailed information for detected Virtual Media URI %s:", uri)
            response = self._request("get", uri)
            LOGGER.debug(json.dumps(response.json(), indent=2))

    def insert_virtual_media(self, image_url):
        "Attaches given image at iDRAC"
        endpoint = f"/Managers/{self.manager_id}/VirtualMedia/RemovableDisk/Actions/VirtualMedia.InsertMedia"
        payload = {'Image': image_url, 'Inserted': True, 'WriteProtected': True}
        self._request("post", endpoint, data=payload)

    def eject_virtual_media(self):
        "Detaches currently attached image at iDRAC"
        endpoint = f"/Managers/{self.manager_id}/VirtualMedia/RemovableDisk/Actions/VirtualMedia.EjectMedia"
        # empty payload is required
        payload = {}
        self._request("post", endpoint, data=payload)
        # some delay is needed after eject, because if next operation
        # right after this one will be inserting, it will fail!
        time.sleep(5)

    def validate_media_status(self, expect_inserted: bool):
        """Checks if image is attached or detached as expected

        Args:
            expect_inserted: True if we expect that image is inserted, False if we expect that image is ejected
        """
        endpoint = f"/Managers/{self.manager_id}/VirtualMedia/RemovableDisk"
        response = self._request("get", endpoint)
        data = response.json()

        LOGGER.info(
            "Virtual Media for RemovableDisk attach status: %s",
            "Inserted" if data["Inserted"] else "Ejected")

        if expect_inserted and not data["Inserted"]:
            raise Exception("Media not attached")
        if not expect_inserted and data["Inserted"]:
            raise Exception("Media not ejected")

    def set_next_onetime_boot_device_virtual_media(self):
        """Sets next one-time boot to Virtual Media.
           Note: This uses Dell-specific Redfish protocol extension.
        """

        endpoint = f"/Managers/{self.manager_id}/Actions/Oem/EID_674_Manager.ImportSystemConfiguration"
        # possible boot devices: vFDD, VCD-DVD
        payload = {
            "ShareParameters": {"Target": "ALL"},
            "ImportBuffer": (
                "<SystemConfiguration>"
                "<Component FQDD=\"iDRAC.Embedded.1\">"
                "<Attribute Name=\"ServerBoot.1#BootOnce\">Enabled</Attribute>"
                "<Attribute Name=\"ServerBoot.1#FirstBootDevice\">vFDD</Attribute>"
                "</Component></SystemConfiguration>")}
        response = self._request("post", endpoint, data=payload)

        # response body is empty, created job id is however contained in headers, so extract it
        job_id = response.headers['Location'].split('/')[-1]

        while True:
            endpoint = f"/TaskService/Tasks/{job_id}"
            response = self._request("get", endpoint)
            status_code = response.status_code
            data = response.json()

            if status_code in (202, 200):
                time.sleep(3)
            else:
                raise Exception(f"Query job ID command failed, error code is: {status_code}")

            message = data['Oem']['Dell']['Message']
            job_state = data['Oem']['Dell']['JobState']
            failed_msgs = (
                "failed", "completed with errors", "Not one", "not compliant", "Unable",
                "The system could not be shut down", "timed out")
            success_msgs = ("Successfully imported", "completed with errors")

            if any((msg in message  for msg in failed_msgs)):
                LOGGER.error(
                    "Job ID %s marked as %s but detected issue(s). "
                    "See detailed job results below for more information on failure", job_id, job_state)
                LOGGER.debug("Detailed job results for job ID %s:", job_id)
                for k, v in data['Oem']['Dell'].items():
                    LOGGER.debug("%s: %s", k, v)
            elif "No changes" in message:
                LOGGER.info("Next onetime boot device already set to Virtual Floppy, no changes applied")
                break
            elif any((msg in message  for msg in success_msgs)):
                LOGGER.info("Successfully set next onetime boot device to Virtual Floppy")
                break
            else:
                time.sleep(1)
                continue

    ###### BOOT OPTIONS ######

    def set_next_boot_device(self, boot_device: str, onetime: bool):
        """Sets next boot to devices other than Virtual Media

        Args:
            boot_device: possible boot devices: None, Pxe, Floppy, Cd, Usb, Hdd, SDCard,
                         BiosSetup, Diags, Utilities, UefiTarget, UefiHttp
            onetime: True to boot selected device only once, False to boot persistently
        """

        endpoint = f"/Systems/{self.system_id}"
        if boot_device == 'None':
            payload = {'Boot': {'BootSourceOverrideEnabled': 'Disabled'}}
        else:
            payload = {'Boot': {
                'BootSourceOverrideEnabled': 'Continuous' if not onetime
                                             else 'Once',
                'BootSourceOverrideTarget': boot_device
            }}

        # those targets require changing from Legacy to UEFI boot mode
        if boot_device in ('UefiTarget', 'UefiHttp'):
            payload['Boot']['BootSourceOverrideMode'] = 'UEFI'

        self._request("patch", endpoint, data=payload)

    def set_boot_method(self, boot_method: str):
        """Change boot method

        Args:
            boot_method: possible boot methods: Legacy, UEFI
        """

        endpoint = f"/Systems/{self.system_id}"
        payload = {'Boot': {'BootSourceOverrideMode': boot_method}}
        self._request("patch", endpoint, data=payload)

    ###### IDRAC SETTINGS OPTIONS ######

    def patch_idrac_attributes(self, attributes: dict):
        """Sends PATCH REST request to /Managers/manager_id/Attributes endpoint.

        Args:
            payload_data: attributes to be send as json into 'Attributes' field.
        Returns:
            requests.Response: received Response object.
        """

        LOGGER.debug("Patching idrac attributes: %s", attributes)
        payload_data = {"Attributes": attributes}
        return self._request("patch",
                             f"/Managers/{self.manager_id}/Attributes",
                             data=payload_data)
