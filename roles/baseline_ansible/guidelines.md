```text
SPDX-License-Identifier: Apache-2.0
Copyright (c) 2021 Intel Corporation
```

<!-- omit in toc -->
# Guidelines

- [General approach to BMRA and CEEK common part abstraction](#general-approach-to-bmra-and-ceek-common-part-abstraction)
  - [Workflow](#workflow)
  - [What should be considered when implementing common part](#what-should-be-considered-when-implementing-common-part)
    - [Part of functionality present only in one team’s product](#part-of-functionalitypresent-only-in-one-teamsproduct)
    - [Keep it simple](#keep-itsimple)
- [Multi OS guidelines](#multi-os-guidelines)
  - [Main task should be OS agnostic](#main-task-should-be-osagnostic)
    - [Package management](#packagemanagement)
    - [OS abstraction](#os-abstraction)
    - [Preferer usage of ansible_os_family](#preferer-usage-ofansible_os_family)
- [General guidelines](#general-guidelines)
  - [Roles should be independent from target host](#roles-should-be-independent-from-targethost)
  - [Roles configurability](#rolesconfigurability)
  - [Tasks files size](#tasks-filessize)
  - [Tasks file should have single responsibility](#tasksfileshould-have-singleresponsibility)
  - [Keep roles output files in one place](#keep-roles-output-files-in-oneplace)
  - [Check host state before execution](#check-host-state-beforeexecution)
  - [“block” usage](#block-usage)
  - [Use command's 'creates' param when possible](#usecommandscreates-param-whenpossible)
  - [Ansible module instead of command](#ansible-module-instead-of-command)
  - ["become: yes" usage](#become-yesusage)
  - [Check error (failed_when) instead of using ignore_error](#check-error-failed_when-instead-of-usingignore_error)
  - [Declare all variables as public](#declare-all-variables-as-public)
  - [Don't remove temporary files if possible](#dont-remove-temporary-files-ifpossible)

## General approach to BMRA and CEEK common part abstraction

Common part abstraction should be done based on functionality separation.

### Workflow

1. Team selects functionality which will be **abstracted**
2. Team starts with functionality analysis in both BMRA and CEEK:
   1. Identify common **elements**
   2. Identify non-common elements which can be set as common (bring additional value)
   3. Evaluate work needed to create common **part**
   4. Present analysis to **other** team and agree on **it**
3. Implement common **part**
4. Integrate common part with team’s **product**
5. Indicate to the other team that common part is **implemented**
6. Other team integrates common part with their product with support of team responsible for creating common **part**

### What should be considered when implementing common part

#### Part of functionality present only in one team’s product

When part of functionality is only present in one product consider two options:

1. Add this functionality to common part and add option to enable it via **variable**
2. Create product depended include which will be present only in product **code**

Option **1** is advised.

#### Keep it simple

Aim of this task is not to refactor both projects and get the best code possible, but firstly having common parts and refactoring can be the next step.

## Multi OS guidelines

### Main task should be OS agnostic

Main tasks should be generic and if needed it should include specialized tasks for a given OS.

#### Package management

Roles should install needed packages using “install_dependencies” role.

#### OS abstraction

Following options are possible:

1. In case there are very few OS dependencies: Use when ansible_os_family for specific **tasks**
2. In case there are many OS dependencies: Create an OS specific file and use include_tasks  
3. Create variables set dependent on OS and include files with vars using include_vars with with_first_found

Each option should be revised individually.

#### Preferer usage of ansible_os_family

OS abstraction should be as general as possible.
In corner cases it is possible to ansible_distribution and ansible_distribution_major_version.

Currently supported OS families:

1. For Centos 7/8 and RHEL: "RedHat"
2. For Ubuntu 20.04: "Debian"

## General guidelines

### Roles should be independent from target host

Roles should not have any checks against which host runs it. Playbook should be the place where role is mapped to host.

### Roles configurability

To avoid dependencies and hardcodes, roles should be configurable using variables.
These variables should tune, enable or disable parts of role.

### Tasks files size

If file contains more than 8 tasks, consider splitting it to separate files.

### Tasks file should have single responsibility

Tasks in one file should have clear and single responsibility. In other case, tasks in such file should be split based on their responsibility.

### Keep roles output files in one place

Roles should keep its files in a well-known directory tree for easier **cleanup**
*Example*:
Keep all files in /opt/bmra or /opt/openness and during cleanup we can carve out whole directory

### Check host state before execution

Check if host state which tasks are trying to set isn’t already active.
*Example*:
When tasks are building library/application firstly these should check if such library/application isn’t already installed/build with intended version before installation/building.

### “block” usage

"block" should be used if it improves readability and removes code duplication.
Blocks can help to group tasks that are executed under a single condition.
When there is too many blocks in single file, consider splitting the blocks into separate files (ref. [Tasks files size](#tasks-filessize), [Tasks file should have single responsibility](#tasksfileshould-have-singleresponsibility)).

### Use command's 'creates' param when possible

If a file specified by 'creates' already exists, this step will not be run.

### Ansible module instead of command

Don't use command and shell when Ansible module is **available**
*Example*:
Instead of:

```yml
command: service auditd restart
```

Use:

```yml
service:
    name: auditd
    state: restarted
```

### "become: yes" usage

“**become: yes**” should be only used when *absolutely necessary*.
It should also be set on smallest element possible. This can be whole role, if “**become**: yes” is needed for all tasks in role.

### Check error (failed_when) instead of using ignore_error

We sometimes check if a feature is already installed by calling a command that can result in an error. We should narrow the accepted error down and fail in other cases.

### Declare all variables as public

All variables should be declared without any prefix which would suggest that the variable is private.

Use:

```yml
public_path: '/foo/bar'
```

instead of:

```yml
_private_path: '/foo/bar'
```

### Don't remove temporary files if possible

The temporary files make debugging a lot **easier**
