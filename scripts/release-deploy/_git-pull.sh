#!/bin/bash

# This is a helper script that is used to pull the latest code from the git repository

# Import common functions and variables
source /$SERVICE_NAME/scripts/utils.sh

# Change directory to the codebase
cd /$SERVICE_NAME

echo "Pulling the latest code from the git repository..."
ssh-agent bash -c "ssh-add ~/.ssh/id_rsa; git pull"
echo "Done."