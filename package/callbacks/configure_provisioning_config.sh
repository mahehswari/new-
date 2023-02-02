#!/bin/bash

set -euxo pipefail

GITHUB_REF=${GITHUB_REF:-}
if [ -z "$GITHUB_REF" ]; then
    echo "\$GITHUB_REF is empty - default config for ESP Provisioning will not change"
    exit 0
fi

# remove "refs/tags/" from the GITHUB_REF
REF="${GITHUB_REF/refs\/tags\//}"

# remove -i in tag (e.g. product-name-open-21.09.01-i-rc1 => product-name-open-21.09.01-rc1)
if [[ $REF =~ ([a-z\-]*[0-9]{2}(\.[0-9]{2})+)\-i[\-]?(.*) ]]; then
    # group 1 & 3 because BASH does not support non-capture groups
    REF="${BASH_REMATCH[1]}"
    if [ -n "${BASH_REMATCH[3]}" ]; then
        REF="${REF}-${BASH_REMATCH[3]}"
    fi
    EK_REF="${REF}"
else
    # -i- not matched - add "-v" to the Experience Kit's tag
    EK_REF="${REF}-v"
fi

# always add -b prefix to the ESP profile's branch
PROFILE_REF="${REF}-b"

CONFIG_PATH="scripts/deploy_esp/default_config.yml"

YQ_VERSION=v4.12.2
YQ_BINARY=yq_linux_amd64

BIN_TEMP_PATH="$(mktemp -d)"
wget https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/${YQ_BINARY} -O "${BIN_TEMP_PATH}/yq"
chmod +x "${BIN_TEMP_PATH}/yq"

# following steps are used to keep the newlines
"${BIN_TEMP_PATH}/yq" \
    eval ".profiles[0].branch = \"${PROFILE_REF}\" | .profiles[0].experience_kit.branch = \"${EK_REF}\"" \
    "${CEEK_PATH}/${CONFIG_PATH}" > "${CEEK_PATH}/${CONFIG_PATH}.new"
diff -U0 -w -b --ignore-blank-lines \
    "${CEEK_PATH}/${CONFIG_PATH}" "${CEEK_PATH}/${CONFIG_PATH}.new" > "${CEEK_PATH}/${CONFIG_PATH}.diff" || true
patch "${CEEK_PATH}/${CONFIG_PATH}" < "${CEEK_PATH}/${CONFIG_PATH}.diff"

cat "${CEEK_PATH}/${CONFIG_PATH}"

rm -rf "${BIN_TEMP_PATH}" "${CEEK_PATH}/${CONFIG_PATH}.new" "${CEEK_PATH}/${CONFIG_PATH}.diff"
