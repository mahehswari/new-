#!/bin/bash
#
# Copyright 2022 Intel Corporation
# SPDX-License-Identifier:
#
# USAGE:
#    ./upload_ov_trigger_to0.sh -v <voucher_filename>
#
# Example of providing voucher filename:
#
#   ./upload_ov_trigger_to0.sh -v abcdef_voucher.txt
#
# Example of providing all arguments:
#
#   ./upload_ov_trigger_to0.sh -o 127.0.0.1 -u apiUser -p password1 -v abcdef_voucher.txt
#   ./upload_ov_trigger_to0.sh -o 127.0.0.1 -u apiUser -p password1 -v abcdef_voucher.txt
#   ./upload_ov_trigger_to0.sh -o 127.0.0.1 -u apiUser -p password1 -v abcdef_voucher.txt

############################################################
# Help                                                     #
############################################################
Help()
{
    # Display Help
    echo "This script is used to upload voucher to owner and trigger TO0"
    echo
    echo "Syntax: ./upload_ov_trigger_to0.sh [-h|o|p|u|v]"
    echo "options:"
    echo "o     Owner IP, if not provided defaults to localhost."
    echo "p     Owner API password, if not provided defaults to blank."
    echo "u     API username, if not provided defaults to apiUser"
    echo "v     Filename of voucher to be uploaded."
    echo "h     Help."
    echo
}

while getopts a:h:o:p:u:v: flag;
do
    case "${flag}" in
        a) attestation_type=${OPTARG};;
        h) Help
           exit 0;;
        o) onr_ip=${OPTARG};;
        p) onr_api_passwd=${OPTARG};;
        u) api_user=${OPTARG};;
        v) voucher=${OPTARG};;
        \?) echo "Error: Invalid Option, use -h for help"
            exit 1;;
    esac
done

if [ -z "$voucher" ]; then
    echo "Voucher filename is mandatory, check usage with -h" >&2
    exit 1
fi

wrk_dir=$(pwd)

default_attestation_type="SECP256R1"
default_onr_ip="localhost"
default_api_user="apiUser"
default_onr_api_passwd=""
onr_port="30042"

attestation_type=${attestation_type:-$default_attestation_type}
onr_ip=${onr_ip:-$default_onr_ip}
api_user=${api_user:-$default_api_user}
onr_api_passwd=${onr_api_passwd:-$default_onr_api_passwd}


extended_voucher=`cat ${voucher}`
upload_voucher=$(curl --silent -w "%{http_code}\n" -D - --digest -u ${api_user}:${onr_api_passwd} --location --request POST "http://${onr_ip}:${onr_port}/api/v1/owner/vouchers/" --header 'Content-Type: text/plain' --data-raw "$extended_voucher" -o guid.txt)
upload_voucher_code=$(tail -n1 <<< "$upload_voucher")
if [ "$upload_voucher_code" = "200" ]; then
    device_guid=`cat guid.txt`
    echo "Success in uploading voucher to owner for device with GUID ${device_guid}"
    echo "GUID of the device is ${device_guid}"
    trigger_to0=$(curl --silent -w "%{http_code}\n" -D - --digest -u ${api_user}:${onr_api_passwd} --location --request GET "http://${onr_ip}:${onr_port}/api/v1/to0/${device_guid}" --header 'Content-Type: text/plain')
    trigger_to0_code=$(tail -n1 <<< "$trigger_to0")
    echo "Success in triggering TO0 for GUID ${device_guid}"
else
    echo "Failure in uploading voucher to owner for device with GUID ${device_guid} with response code: ${upload_voucher_code}"
fi
