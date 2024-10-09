#!/bin/bash

# This is a helper script that is used to build the Docker image and push it to the Artifact Registry
# Don't use this script locally

# Import common functions and variables
source /$SERVICE_NAME/scripts/utils.sh  # $SERVICE_NAME is set in make-deployment.sh

# Change directory to the codebase
cd /$SERVICE_NAME

# Build, tag, and push the Docker image
echo "Building the Docker image; version $(cat VERSION)..."
docker build -t $SERVICE_NAME:local .
docker tag $SERVICE_NAME:local $ARTIFACT_REPO_URL/$SERVICE_NAME:$(cat VERSION)
docker tag $SERVICE_NAME:local $ARTIFACT_REPO_URL/$SERVICE_NAME:latest
echo "Pushing the Docker image..."
docker push $ARTIFACT_REPO_URL/$SERVICE_NAME:$(cat VERSION)
docker push $ARTIFACT_REPO_URL/$SERVICE_NAME:latest
echo "Done; version $(cat VERSION)"