#!/bin/bash

# This is a helper script that is used to build the Docker image and push it to the Artifact Registry

# Import common functions and variables
source /$SERVICE_NAME/scripts/utils.sh

# Change directory to the codebase
cd /$SERVICE_NAME

# Build, tag, and push the Docker image
echo "Building the Docker image..."
docker build -t $SERVICE_NAME:local .
docker tag $SERVICE_NAME:local $ARTIFACT_REPO_URL/$SERVICE_NAME:$(cat VERSION)
docker tag $SERVICE_NAME:local $ARTIFACT_REPO_URL/$SERVICE_NAME:latest
echo "Pushing the Docker image..."
docker push $ARTIFACT_REPO_URL/$SERVICE_NAME:$(cat VERSION)
echo "Done."