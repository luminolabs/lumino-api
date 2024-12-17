#!/bin/bash

# This script is used to restart the service on the MIG VMs, after make-deployment.sh has been run
# Run this script locally, after make-deployment.sh has been run

# Inputs
SERVICE_NAME=$1
DEPLOY_ENV=$2

# Import common functions and variables
source ./scripts/release-deploy/common.sh

echo "About to delete instances in the MIG group: $SERVICE_NAME. Instances will be recreated automatically."

# If a version is provided, use it;
# Set docker image tag to latest in artifact registry to the version provided
if [ -n "$1" ]; then
  VERSION=$1
  echo "Updating service to use version: $VERSION"
  gcloud artifacts docker tags add \
    $ARTIFACT_REPO_URL/$SERVICE_NAME:$VERSION \
    $ARTIFACT_REPO_URL/$SERVICE_NAME:latest > /dev/null
else
  VERSION=$(cat VERSION)
  echo "No version provided, update latest tag to $VERSION"
  gcloud artifacts docker tags add \
    $ARTIFACT_REPO_URL/$SERVICE_NAME:$VERSION \
    $ARTIFACT_REPO_URL/$SERVICE_NAME:latest > /dev/null
fi

# Start the rolling update
echo "Starting the rolling update."
# Flags:
# --max-unavailable=0: Our minimum number of instances is 1, so we can't have any unavailable
# --min-ready=Xs: Wait for X seconds (see utils.sh) after an instance is ready before considering it available
gcloud beta compute instance-groups managed rolling-action replace $SERVICE_NAME \
  --project=$PROJECT_ID --zone=$ZONE \
  --max-unavailable=0 --min-ready=${BUILD_DURATION_S}s > /dev/null
echo "Rolling update started and *this script will exit now* - it may take up to 5 minutes for the update to complete."
echo "Monitor progress at: https://console.cloud.google.com/compute/instanceGroups/details/$ZONE/$SERVICE_NAME"
echo "Done."