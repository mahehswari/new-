```text
SPDX-License-Identifier: Apache-2.0
Copyright (c) 2021 Intel Corporation
```

## firewall

---

1. Role `firewall_prepare` must be included before any port openings in a playbook.
The `use_firewall=true` variable needs to be specified to include firewall usage. By default firewall will **not** be used.
This role will unmask, enable nad start firewall service as well as do basic configuration.
