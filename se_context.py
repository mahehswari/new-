# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

"""
Provide context for the generic SE Install and Upgrade Toolchain commands to run correctly. The se_build.py script will
replace this file in the offline installation package it builds.
"""

TOOLCHAIN_CFG = {
    "product": {
        "name": "Intel® Smart Edge Open Developer Experience Kit",
        "version": "22.09-dev"
    },
    "context": {
        "offline_flag": False
    },
    "path": {
        "part": {
            "data": "iut/data",
            "dependencies": "se_requirements.txt",
            "docs": None,
            "hooks": "iut",
            "logs": "logs",
            "monitoring_service": "iut/monitoring",
            "package": {
                "docs": "docs",
                "metadata": "metadata.yml",
                "monitoring_service": "monitoring-service.tar",
                "config": "se.yaml",
                "checksum":{
                    "datafiles": "package.sha",
                    "metafiles": "metadata.sha"
                },
            },
            "report_config": "iut/data/report.json",
            "scripts": "scripts",
            "toolchain": "scripts/deploy_esp"
        },
        "full": {
            "repo": None
        }
    },
    "docs": {
        "url": "https://github.com/intel-innersource/applications.services.smart-edge-open.docs",
        "path": "experience-kits/provisioning",
        "branch": "feature/install-upgrade-toolchain",
        "map": [["^IUT-\\d+$", "install-and-upgrade-toolchain.md"]]
    },
    "profile": {
        "name": "Smart_Edge_Open_Developer_Experience_Kits",
        "url": "https://github.com/intel-innersource/applications.services.smart-edge-open.profiles.git",
        "branch": "main"
    },
    "configs": {
        "default":
"""
configurations:
  - name: dek-config
    group_vars:
      all:
        telemetry_enable: false
        sriov_network_operator_configure_enable: false
        sriov_network_operator_enable: false
        e810_driver_enable: false
        sgx_enabled: false
        platform_attestation_node: false
        proxy_env:
          http_proxy: null
          https_proxy: null
          ftp_proxy: null
          no_proxy: null

experience_kits:
  - name: developer-experience-kit-open
    path: .

clusters:
  - name: cluster1
    experience_kit:
      name: developer-experience-kit-open
      deployment: dek
      configuration: dek-config
    hosts:
      controller_group:
        - name: controller
          bmc:
            address: null
            username: null
            password: null

accounts:
  - name: default
    username: seo
    password: null

dhcp_client_address_freeze: false
"""
    }
}
