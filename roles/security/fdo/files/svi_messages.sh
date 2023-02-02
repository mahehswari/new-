#!/bin/bash

ONR_IP=$1
ONR_PORT=$2
ONR_PASSWORD=$3

ONR_SVI_URL="https://$ONR_IP:$ONR_PORT/api/v1/owner/svi"

echo "Update Rendezvous info on the manufacturer service"
http_response=$(curl -o /dev/null -k -s -w "%{http_code}\n" -D - --digest -u apiUser:$ONR_PASSWORD \
  --location --request POST $ONR_SVI_URL \
  --header 'Content-Type: text/plain' \
  --data-raw '[{"filedesc" : "test.sh", "resource" : "test.sh"}, {"exec_cb" : ["/bin/bash","test.sh","test"]}]' | \
  tail -n 1 | cut -d$' ' -f2)
if [ $http_response -ne 200 ]; then
    echo "Failed to update svi messages to owner. Exiting.."
    exit 1
fi
echo "Svi message update to owner successful"
