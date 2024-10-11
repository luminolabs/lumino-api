#!/bin/bash

# This is a helper script that is used to pull the latest code from the git repository
# Don't use this script locally

# Import common functions and variables
source /$SERVICE_NAME/scripts/utils.sh  # $SERVICE_NAME is set in make-deployment.sh

# Change directory to the codebase
cd /$SERVICE_NAME

echo "Pulling the latest code from the git repository..."
git config --global --add safe.directory /$SERVICE_NAME
# Need to disable StrictHostKeyChecking
# because known_hosts file is not available in the ssh-agent environment
# There's probably a better way to do this, but I time boxed this
ssh-agent bash -c "ssh-add ~/.ssh/id_rsa; git -c core.sshCommand='ssh -o StrictHostKeyChecking=no' pull"
echo "Done."