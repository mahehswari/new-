#!/bin/sh
#
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2019-2021 Intel Corporation

# This script generates 4096 bits RSA public­private key pair and a certificate. 
# Certificate is valid for 365 days and signed with CA if CA key and certificate directory is defined

echo "Generating key..."

if [ -f "$2/key.pem" ] && [ -f "$2/cert.pem" ]; then
    echo "Key and certificate pair already exist, skipping..."
    exit 0
fi

if ! openssl version | awk '$2 ~ /(^0\.)|(^1\.(0\.|1\.0))/ { exit 1 }'; then
	echo "Not supported openssl:"
	openssl version
fi

openssl="openssl"
if ! $openssl version | grep 1.1.1; then
    openssl="/usr/local/bin/openssl"
fi

$openssl genrsa -out "$2/key.pem" 4096

if [ -z "$3" ]; then
    echo "Generating certificate..."
    $openssl req -key "$2/key.pem" -new -x509 -days 365 -out "$2/cert.pem" -subj "/C=US/O=Intel Corporation/OU=Smart Edge" -addext "subjectAltName=DNS:$1"
else
    echo "Generating certificate signing request..."
    $openssl req -new -key "$2/key.pem" -out "$2/request.csr" -subj "/C=US/O=Intel Corporation/OU=Smart Edge" -addext "subjectAltName=DNS:$1"

    echo "Signing certificate with $3..."

    extfile=$(mktemp /tmp/ssl-ext-x509.XXXXXX)
    cat << EOF > "$extfile"
[v3_ca]
basicConstraints = CA:FALSE
subjectAltName = DNS:$1
EOF

    $openssl x509 -req -in "$2/request.csr" -CA "$3/cert.pem" -CAkey "$3/key.pem" -days 365 -out "$2/cert.pem" -CAcreateserial -extensions v3_ca -extfile "$extfile"
    cd "$2" || exit 1
    ln -s root.pem "$($openssl x509 -hash -noout -in root.pem).0"
    rm -fv "$extfile"
fi

chmod 644 "$2/key.pem"
