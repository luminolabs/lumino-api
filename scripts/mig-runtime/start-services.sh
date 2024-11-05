#!/bin/bash

# This script is used to start the service on dev and production environments
# Don't use this script locally

# Inputs
SERVICE_NAME=$1
COMPOSE_OPTS="${@:2}"  # Additional options to pass to docker compose

echo "Starting $SERVICE_NAME..."
echo "COMPOSE_OPTS set to $COMPOSE_OPTS"

# Change to the service directory
cd /$SERVICE_NAME

# Import common functions and variables
source ./scripts/utils.sh

# Export .env environment variables
set -o allexport
eval $(cat ./.env | grep -v '^#' | tr -d '\r')
echo "CAPI_ENV set to $CAPI_ENV"

echo "Fetching secrets from Secret Manager"
SECRET_NAME="$SERVICE_NAME-config-$CAPI_ENV"
SECRET_PAYLOAD=$(gcloud secrets versions access latest --secret=$SECRET_NAME --project=$PROJECT_ID)
# Parse the secret payload and set environment variables
eval "$SECRET_PAYLOAD"

echo "Pull the latest image"
docker pull $ARTIFACT_REPO_URL/$SERVICE_NAME:latest
echo "Starting services with docker-compose"
docker compose up -d $COMPOSE_OPTS
echo "Services started successfully"