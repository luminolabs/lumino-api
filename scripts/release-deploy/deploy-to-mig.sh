#!/bin/bash

# This script is used to restart the service on the MIG VMs, after make-deployment.sh has been run
# Run this script locally, after make-deployment.sh has been run

# Inputs
SERVICE_NAME=$1
DEPLOY_ENV=$2

# Import common functions and variables
source ./scripts/release-deploy/utils.sh

echo "About to delete instances in the MIG group: $SERVICE_NAME. Instances will be recreated automatically."

# Pull the version from the VERSION file
# if you'd like to roll back to a previous version, you can manually change the VERSION file
VERSION=$(cat VERSION)

# Make the current version the default version to be used by the MIG
gcloud artifacts docker tags add \
  $ARTIFACT_REPO_URL/$SERVICE_NAME:$VERSION \
  $ARTIFACT_REPO_URL/$SERVICE_NAME:latest > /dev/null

# Start the rolling update
echo "Starting the rolling update."
tofu apply -auto-approve
echo "Rolling update started and *this script will exit now* - it may take up to 5 minutes for the update to complete."
echo "Monitor progress at: https://console.cloud.google.com/compute/instanceGroups/details/$ZONE/$SERVICE_NAME-mig"
echo "Done."