#!/bin/bash

# Function to check if a string value is truthy
is_truthy() {
  local value=$1
  if [[ "$value" == "yes" ]] || [[ "$value" == "1" ]] || [[ "$value" == "true" ]]; then
    echo "1"
    return
  fi
  echo "0"
}

# GCP / Build variables
RESOURCES_PROJECT_ID="neat-airport-407301"
REGION="us-central1"
ZONE="us-central1-a"
ARTIFACT_REPO_URL="$REGION-docker.pkg.dev/$RESOURCES_PROJECT_ID/lum-docker-images"
BUILD_VM="scheduler-zen"
BUILD_DURATION_S=60  # 60 seconds
CODE_REPO_DIR="/$SERVICE_NAME"

# Set the project ID and service account based on the environment
PROJECT_ID="eng-ai-$DEPLOY_ENV"

# Echo variables for debugging
echo "Current directory: $(pwd)"
echo "DEPLOY_ENV set to $DEPLOY_ENV"
echo "PROJECT_ID set to $PROJECT_ID"