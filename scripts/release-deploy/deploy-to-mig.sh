#!/bin/bash

# This script is used to restart the service on the MIG VMs, after make-deployment.sh has been run
# Run this script locally, after make-deployment.sh has been run

# Import common functions and variables
source ./scripts/utils.sh  # Sets $SERVICE_NAME

echo "About to delete instances in the MIG group: $SERVICE_NAME-prod. Instances will be recreated automatically."

# If a version is provided, use it;
# Set docker image tag to latest in artifact registry to the version provided
if [ -n "$1" ]; then
  VERSION=$1
  echo "Updating service to use version: $VERSION"
  gcloud artifacts docker tags add \
    $ARTIFACT_REPO_URL/$SERVICE_NAME:$VERSION \
    $ARTIFACT_REPO_URL/$SERVICE_NAME:latest > /dev/null
else
  echo "No version provided, using the latest image tag."
fi

# Get the current list of VMs before the update (Old VMs)
OLD_VMS=$(gcloud compute instance-groups managed list-instances $SERVICE_NAME-prod \
  --project=$PROJECT_ID --zone=$WORK_ZONE \
  --format="value(name)")

# Get the current MIG target size (the desired number of instances)
TARGET_SIZE=$(gcloud compute instance-groups managed describe $SERVICE_NAME-prod \
  --project=$PROJECT_ID --zone=$WORK_ZONE \
  --format="value(targetSize)")

# Start the rolling update
echo "Starting the rolling update."
# Flags:
# --max-unavailable=0: Our minimum number of instances is 1, so we can't have any unavailable
# --min-ready=60s: Wait for 60 seconds after an instance is ready before considering it available
gcloud beta compute instance-groups managed rolling-action replace $SERVICE_NAME-prod \
  --project=$PROJECT_ID --zone=$WORK_ZONE \
  --max-unavailable=0 --min-ready=${BUILD_DURATION}s > /dev/null
echo "Rolling update started and *this script will exit now* - it may take a few minutes for the update to complete."
echo "Done."