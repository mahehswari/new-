#!/bin/bash

ONR_IP=$1
ONR_PORT=$2
ONR_PASSWORD=$3
FILE_NAME=$4
FILE_PATH=$5

ONR_SVI_URL="https://$ONR_IP:$ONR_PORT/api/v1/owner/resource?filename="$FILE_NAME

echo "Upload svi file to owner"
http_response=$(curl -o /dev/null -k -s -w "%{http_code}\n" -D - --digest -u apiUser:$ONR_PASSWORD \
  --location --request POST $ONR_SVI_URL \
  --header 'Content-Type: text/plain' \
  --data-binary '@'$FILE_PATH | \
  tail -n 1 | cut -d$' ' -f2)
if [ $http_response -ne 200 ]; then
    echo "Failed to upload svi file to owner. Exiting.."
    exit 1
fi
echo "Svi file upload to owner successful"
