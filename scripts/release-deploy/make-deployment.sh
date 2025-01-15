#!/bin/bash

# This script is used to orchestrate the build process
# Run this script locally, before running deploy-to-mig.sh

# Prerequisites:
# - You need to be in `builders` and `docker` groups in the builder VM
# - You need your github private key in ~/.ssh/id_rsa in the builder VM
# Contact Vasilis if you need help with this

# Constants
SERVICE_NAME='lumino-api'

# Inputs
DEPLOY_ENV=$1

echo "Starting the build process for $SERVICE_NAME..."

# Import common functions and variables
source ./scripts/release-deploy/utils.sh

# Pull the latest code from the repository
stty -echo  # Hide the user input, so the password is not displayed
gcloud compute ssh $BUILD_VM --project=$RESOURCES_PROJECT_ID --zone=$ZONE \
      --command="CODE_REPO_DIR=$CODE_REPO_DIR $CODE_REPO_DIR/scripts/release-deploy/_git-pull.sh"
stty echo  # Restore the user input

# Build the docker image
gcloud compute ssh $BUILD_VM --project=$RESOURCES_PROJECT_ID --zone=$ZONE \
      --command="CODE_REPO_DIR=$CODE_REPO_DIR SERVICE_NAME=$SERVICE_NAME ARTIFACT_REPO_URL=$ARTIFACT_REPO_URL $CODE_REPO_DIR/scripts/release-deploy/_make-docker-image.sh"

echo "Done."