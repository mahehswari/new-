#!/bin/bash
#
# Copyright 2022 Intel Corporation
# SPDX-License-Identifier:
#
# USAGE:
#    ./get_owner_cert.sh
#
# Example of providing all arguments:
#
#   ./get_owner_cert.sh -a SECP256R1 -o 127.0.0.1 -u apiUser -p password2
#   ./get_owner_cert.sh -a SECP384R1 -o 127.0.0.1 -u apiUser -p password2
#   ./get_owner_cert.sh -a RSA2048RESTR -o 127.0.0.1 -u apiUser -p password2

############################################################
# Help                                                     #
############################################################
Help()
{
    # Display Help
    echo "This script is used to download owner certificate."
    echo
    echo "Syntax: ./get_owner_cert.sh [-a|h|o|p|u]"
    echo "options:"
    echo "a     Certificate Attestation type to be retrieved, if not provided defaults to SECP256R1."
    echo "o     Owner IP, if not provided defaults to localhost."
    echo "p     Owner API password, if not provided defaults to blank."
    echo "u     API username, if not provided defaults to apiUser"
    echo "h     Help."
    echo
}

while getopts a:e:h:o:p:u: flag;
do
    case "${flag}" in
        a) attestation_type=${OPTARG};;
        h) Help
           exit 0;;
        o) onr_ip=${OPTARG};;
        p) onr_api_passwd=${OPTARG};;
        u) api_user=${OPTARG};;
        \?) echo "Error: Invalid Option, use -h for help"
            exit 1;;
    esac
done

default_attestation_type="SECP256R1"
default_onr_ip="localhost"
default_api_user="apiUser"
default_onr_api_passwd=""
onr_port="30042"

attestation_type=${attestation_type:-$default_attestation_type}
mfg_ip=${mfg_ip:-$default_mfg_ip}
api_user=${api_user:-$default_api_user}
mfg_api_passwd=${mfg_api_passwd:-$default_mfg_api_passwd}

get_cert=$(curl --silent -w "%{http_code}\n" -D - --digest -u ${api_user}:${onr_api_passwd} --location --request GET "http://${onr_ip}:${onr_port}/api/v1/certificate?alias=${attestation_type}" -H 'Content-Type: text/plain' -o owner_cert.txt)
get_cert_code=$(tail -n1 <<< "$get_cert")
if [ "$get_cert_code" = "200" ]; then
    echo "Success in downloading ${attestation_type} owner certificate to owner_cert.txt"
else
    echo "Failure in getting owner certificate for type ${attestation_type} with response code: ${get_cert_code}"
fi
