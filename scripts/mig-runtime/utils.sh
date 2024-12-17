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

# Export all variables
set -o allexport

# GCP / Build variables
RESOURCES_PROJECT_ID="neat-airport-407301"
REGION="us-central1"
ZONE="us-central1-a"
ARTIFACT_REPO_URL="$REGION-docker.pkg.dev/$RESOURCES_PROJECT_ID/lum-docker-images"
BUILD_VM="scheduler-zen"
BUILD_DURATION_S=60  # 60 seconds
ENV_VAR_PREFIX="CAPI"
CODE_REPO_DIR="/$SERVICE_NAME"

# Environment variables
LOCAL_ENV="local"
IS_GCP="0"

# Check if the folder exists
if [ -d "$CODE_REPO_DIR" ]; then
    cd "$CODE_REPO_DIR" || exit 0
fi

# See if .gcp file exists, which indicates we're running on GCP
if [ -f ./.gcp ]; then
  IS_GCP="1"
fi

if [[ $(is_truthy "$IS_GCP") == "1" ]]; then
  CAPI_ENV=$(curl -s -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/attributes/${ENV_VAR_PREFIX}_ENV")
else
  CAPI_ENV=$LOCAL_ENV
fi

# If we're running locally, export variables from the .env file
if [[ $(is_truthy "$IS_GCP") == "0" ]]; then
  eval $(cat ./.env | grep -v '^#' | tr -d '\r')
fi

# Set the project ID and service account based on the environment
PROJECT_ID="eng-ai-$CAPI_ENV"
SERVICE_ACCOUNT="$SERVICE_NAME-sa@$PROJECT_ID.iam.gserviceaccount.com"
CLOUDSDK_CORE_ACCOUNT=$SERVICE_ACCOUNT

# Echo variables for debugging
echo "Current directory: $(pwd)"
echo "IS_GCP set to $IS_GCP"
echo "CAPI_ENV set to $CAPI_ENV"
echo "PROJECT_ID set to $PROJECT_ID"
echo "SERVICE_ACCOUNT set to $SERVICE_ACCOUNT"
echo "CLOUDSDK_CORE_ACCOUNT set to $CLOUDSDK_CORE_ACCOUNT"