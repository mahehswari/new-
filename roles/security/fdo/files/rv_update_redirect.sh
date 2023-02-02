#!/bin/bash

MFG_IP=$1
MFG_PORT=$2
MFG_PASSWORD=$3
RV_IP=$4
RV_PORT=$5
OWNER_IP=$6
OWNER_PORT=$7
OWNER_PASSWORD=$8
RV_DNS_IP=${10:-$RV_IP}
RV_DNS_PORT=${11:-$RV_PORT}

MFG_SVC_URL="https://$MFG_IP:$MFG_PORT/api/v1/rvinfo"
OWNER_REDIRECT_URL="https://$OWNER_IP:$OWNER_PORT/api/v1/owner/redirect"

echo "Update Rendezvous info on the manufacturer service"
http_response=$(curl -o /dev/null -k -s -w "%{http_code}\n" -D - --digest -u apiUser:$MFG_PASSWORD \
  --location --request POST $MFG_SVC_URL \
  --header 'Content-Type: text/plain' \
  --data-raw "[[[5,\"$RV_DNS_IP\"],[3,$RV_DNS_PORT],[12,2],[2,\"$RV_IP\"],[4,$RV_PORT]]]" | \
  tail -n 1 | cut -d$' ' -f2)
if [ $http_response -ne 200 ]; then
    echo "Failed to update rvinfo on manufaturer. Exiting.."
    exit 1
fi
echo "rvinfo update on manufacturer Success!!!"

echo "Update owner re-direction for device"
http_response=$(curl -o /dev/null -k -s -w "%{http_code}\n" -D - --digest -u apiUser:$OWNER_PASSWORD \
  --location --request POST $OWNER_REDIRECT_URL \
  --header 'Content-Type: text/plain' \
  --data-raw "[[\"$OWNER_IP\", \"$OWNER_IP\", $OWNER_PORT, 5]]" | \
  tail -n 1 | cut -d$' ' -f2)
if [ $http_response -ne 200 ]; then
    echo "Failed to update owner re-direction. Exiting.."
    exit 1
fi
echo "owner redirect update Success!!!"
