```text
SPDX-License-Identifier: Apache-2.0
Copyright (c) 2022 Intel Corporation
```

# install comms package

---

This role installs the Intel® Ethernet 800 Series Telecommunication (Comms) Dynamic Device Personalization (DDP) Package for E810 NICs resulting in update DDP profile.
The package is loaded by the ice driver.


The role requires the following variables to be defined:

ice_comms_package_url
ice_comms_package_checksum
ice_comms_package_version
current_mgmt_driver

It is expected that appropriate version of ICE driver is loaded. For examples on loading the driver see 'build_nic_drivers' role.
The requirements could be satisfied like:

```yaml
# put the ice_* vars to defaults/main.yml for ease of maintenance
- name: enable ice comms package
    block:
      - name: set facts
        set_fact:
          ice_comms_package_url: "{{ _ice_comms_url }}"
          ice_comms_package_checksum: "{{ _ice_comms_chksm }}"
          ice_comms_package_version: "{{ _ice_comms_ver }}"
          current_mgmt_driver: "{{ _mgmt_driver }}"

      - name: install ice comms package
        include_role:
          name: baseline_ansible/infrastructure/install_comms_pkg
    when: e810_comms_pkg_enable | default(False)
```
