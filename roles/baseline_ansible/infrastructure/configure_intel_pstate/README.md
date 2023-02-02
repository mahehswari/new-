```text
SPDX-License-Identifier: Apache-2.0
Copyright (c) 2021 Intel Corporation
```

# configure_intel_pstate

Confiure intel_pstate driver and the turbo mode.
The input is validated.

For more information, visit https://www.kernel.org/doc/html/v4.12/admin-guide/pm/intel_pstate.html

Example usage:
```yaml
intel_pstate_configuration_enabled: true

# Available intel_pstate driver configuration options:
#  - disable
#  - passive
#  - force
#  - no_hwp
#  - hwp_only
#  - support_acpi_ppc
#  - per_cpu_perf_limits
intel_pstate_configuration: disable

turbo_configuration_enabled: true
turbo_active: false # disables turbo
```
