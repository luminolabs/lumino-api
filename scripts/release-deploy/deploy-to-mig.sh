#!/bin/bash

# This script is used to restart the service on the MIG VMs, after make-deployment.sh has been run
# Run this script locally, after make-deployment.sh has been run

# Constants
SERVICE_NAME='lumino-api'
VERSION=$(cat VERSION)  # If you'd like to roll back to a previous version, change the VERSION file to the desired version

# Inputs
DEPLOY_ENV=$1

echo "Starting the deploy process for $SERVICE_NAME in $DEPLOY_ENV..."

# Switching to the DEPLOY_ENV terraform workspace
tofu workspace select $DEPLOY_ENV

# Import common functions and variables
source ./scripts/release-deploy/utils.sh

# Make the current version the default version to be used by the MIG
gcloud artifacts docker tags add \
  $ARTIFACT_REPO_URL/$SERVICE_NAME:$VERSION \
  $ARTIFACT_REPO_URL/$SERVICE_NAME:latest > /dev/null

echo "Starting the rolling update."
cd terraform && tofu apply -var-file="$DEPLOY_ENV.tfvars" -var-file="secrets.tfvars"
echo "Rolling update started and *this script will exit now* - it may take up to 5 minutes for the update to complete."
echo "Monitor progress at: https://console.cloud.google.com/compute/instanceGroups/details/$ZONE/$SERVICE_NAME-mig"

echo "Done."