#!/bin/bash

# This is a helper script that is used to build the Docker image and push it to the Artifact Registry
# This script is run in the builder VM, by make-deployment.sh - don't run this script directly
# Don't use this script locally

# Change directory to the codebase
cd $CODE_REPO_DIR

# Constants
VERSION=$(cat VERSION)

echo "Building the Docker image; version $VERSION..."
docker build -t $SERVICE_NAME:local .
docker tag $SERVICE_NAME:local $ARTIFACT_REPO_URL/$SERVICE_NAME:$VERSION
docker tag $SERVICE_NAME:local $ARTIFACT_REPO_URL/$SERVICE_NAME:latest

echo "Pushing the Docker image..."
docker push $ARTIFACT_REPO_URL/$SERVICE_NAME:$VERSION
docker push $ARTIFACT_REPO_URL/$SERVICE_NAME:latest

echo "Done; version $VERSION"