#!/bin/bash

# This is a helper script that is used to pull the latest code from the git repository
# This script is run in the builder VM, by make-deployment.sh - don't run this script directly
# Don't use this script locally

# Change directory to the codebase
cd $CODE_REPO_DIR

echo "Pulling the latest code from the git repository..."
git config --global --add safe.directory $CODE_REPO_DIR
# Need to disable StrictHostKeyChecking
# because known_hosts file is not available in the ssh-agent environment
# There's probably a better way to do this, but I time boxed this
ssh-agent bash -c "ssh-add ~/.ssh/id_rsa; git -c core.sshCommand='ssh -o StrictHostKeyChecking=no' pull"

echo "Done."