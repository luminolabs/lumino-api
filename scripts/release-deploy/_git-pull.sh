#!/bin/bash

# This is a helper script that is used to pull the latest code from the git repository

# Import common functions and variables
source ./scripts/utils.sh

echo "Pulling the latest code from the git repository..."
# Add the SSH key to the ssh-agent to authenticate with the git repository
ssh-agent bash -c "ssh-add ~/.ssh/id_rsa; git pull"
# Pull the latest code from the git repository
git pull
echo "Done."