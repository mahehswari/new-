#!/bin/bash

DEVICE_BIN=./build/linux-client
MFG_SN_FILE=./data/manufacturer_sn.bin
SN_FILE=./device_serial_number

if [ -f "$SN_FILE" ]; then
    echo "$SN_FILE exists"
    echo "Device Init is already done. Starting TO1"
else
    echo "Starting Device Init"
    # Generate random serial number using 12 characters of random
    # alphanumeric characters in the set A-Za-z0-9 and 13 numeric
    # characters obtained from the system's current timestamp.
    SN_PART_1=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 12 ; echo '')
    SN_PART_2=$(($(date +%s%N)/1000000))

    SL_NUM=$SN_PART_1$SN_PART_2

    # Save the serial number in maufacturer_sn.bin, the
    # default path for the device serial number that is
    # read during Device Init (DI) at manufacturer.
    echo -n $SL_NUM > $MFG_SN_FILE
fi

# Invoke DI for the device to register it with the manufacturer
$DEVICE_BIN -ss

RESULT=$?

# Check for success and then write the serial number
# into the device_serial_number file. This file can
# be used as a signal of successful DI.
if [ -f "$SN_FILE" ]; then
    if [ $RESULT -eq 0 ]; then
        echo "Device onboarding successful"
	echo "Disabling fdo-client service for next device boot"
	systemctl disable fdo-client
    else
	echo "Device onboarding failed during TO1/TO2"
    fi
else
    if [ $RESULT -eq 0 ]; then
        echo "Device Init successful"
        echo -n $SL_NUM > $SN_FILE
    else
	echo "Device Init failed. Please try again"
    fi
fi

