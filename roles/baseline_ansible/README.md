```text
SPDX-License-Identifier: Apache-2.0
Copyright (c) 2021 Intel Corporation
```

# baseline-ansible

baseline-ansible collections provide generic roles, modules & plugins to accelerate development of your ansible playbooks.

## Quickstart Usage
1. Update your ansible.cfg settings collection path
    ```
    [defaults]
    collections_paths=./ansible_collections
    ```

1. Install collections in root of your project.
    ```
    ansible-galaxy collection install git@github.com:intel-innersource/applications.services.smart-edge-open.baseline-ansible/ -p ./
    ```

1. Alternativly, create a requirements file and install in root of your project.
    ```
    vi requirements.yml
    ansible-galaxy collection install -r collections/requirements.yml
    ```
    Note: format of requirments.yml
    ```
    	collections:
	  - name: baseline_ansible.time
	    src: ssh://git@github.com/intel-innersource/applications.services.smart-edge-open.baseline-ansible.git
	    path: ./
            scm: git
    ```

1. Update your playbooks to reference the desired collection and role.
    ```
    hosts: all
      collections:
        - baseline_ansible.time
      tasks: []
      roles:
        - role: ntp_install
    ```

## Collection Development
1. Create and Edit collection templates for each set of roles

    - Create template directory structure
    ```
    ansible-galaxy collection init baseline_ansible.time
    ansible-galaxy collection init baseline_ansible.machine_setup
    ansible-galaxy collection init baseline_ansible.telemetry
    etc…
    ```
    Note: role tree needs to be flat - no subdirectories
    
    - Edit roles as necessary. i.e.
    ```
    vi baseline_ansible/time/roles/ntp_install/tasks/main.yml
    ```

1. Build and Install each collection tar for local testing
    - In root of a given collection. i.e. time
    ```
    ansible-galaxy collection build
    ```
    - In root of playbook needing to reference the collection 
    ```
    ansible-galaxy collection install ../../baseline-ansible/baseline_ansible/time/baseline_ansible-time-1.0.0.tar.gz -p ./ansible_collections
	
    ansible-galaxy collection install../../baseline-ansible/baseline_ansible/machine_setup/baseline_ansible-machine_setup-1.0.0.tar.gz -p ./ansible_collections
    
    etc...
    ```
