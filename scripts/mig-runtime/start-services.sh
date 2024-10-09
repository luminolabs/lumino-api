#!/bin/bash

# This script is used to start the service on dev and production environments
# Don't use this script locally

# $SERVICE_NAME is set in /etc/environment
echo "Starting $SERVICE_NAME..."

# Inputs
COMPOSE_OPTS="${@:1}"  # Additional options to pass to docker compose
echo "COMPOSE_OPTS set to $COMPOSE_OPTS"

# Change to the service directory
cd /$SERVICE_NAME

# Import common functions and variables
source ./scripts/utils.sh

# Export .env environment variables; note, we aren't aware of which environment
# we're running on before importing CAPI_ENV from .env,
# so we can't cd to /pipeline-zen-jobs conditionally above
eval $(cat ./.env | grep -v '^#' | tr -d '\r')
echo "CAPI_ENV set to $CAPI_ENV"

echo "Fetching secrets from Secret Manager"
SECRET_NAME="$SERVICE_NAME-config-$CAPI_ENV"
SECRET_PAYLOAD=$(gcloud secrets versions access latest --secret=$SECRET_NAME --project=$PROJECT_ID)
# Parse the secret payload and set environment variables
eval "$SECRET_PAYLOAD"

# Export the variables so they're available to docker-compose
export CAPI_DB_NAME
export CAPI_DB_USER
export CAPI_DB_PASS
export CAPI_AUTH0_CLIENT_ID
export CAPI_AUTH0_CLIENT_SECRET
export CAPI_AUTH0_DOMAIN
export CAPI_APP_SECRET_KEY
export CAPI_STRIPE_SECRET_KEY
export CAPI_STRIPE_WEBHOOK_SECRET

echo "Pull the latest image"
docker pull $ARTIFACT_REPO_URL/$SERVICE_NAME:latest
echo "Starting services with docker-compose"
docker compose up -d $COMPOSE_OPTS
echo "Services started successfully"
