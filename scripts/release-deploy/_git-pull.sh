#!/bin/bash

# This is a helper script that is used to pull the latest code from the git repository
# Don't use this script locally

# Import common functions and variables
source /$SERVICE_NAME/scripts/utils.sh  # $SERVICE_NAME is set in make-deployment.sh

# Change directory to the codebase
cd /$SERVICE_NAME

echo "Pulling the latest code from the git repository..."
ssh-agent bash -c "ssh-add ~/.ssh/id_rsa; git pull"
echo "Done."