#!/bin/bash

# This script is used to start all services on dev and production environments, don't use locally

# Exit on errors
set -e

# Inputs
COMPOSE_OPTS=$1  # Additional options to pass to docker compose

LOCAL_ENV="local"
PROJECT_ID="neat-airport-407301"
SECRET_NAME_PREFIX="lumino-api-config"

if [[ "$CAPI_ENV" == "" ]]; then
  CAPI_ENV="$LOCAL_ENV"
fi

# Export .env environment variables; note, we aren't aware of which environment
# we're running on before importing CAPI_ENV from .env,
# so we can't cd to /pipeline-zen-jobs conditionally above
eval $(cat ./.env | grep -v '^#' | tr -d '\r')
echo "CAPI_ENV set to $CAPI_ENV"

# Fetch the secret
echo "Fetching secrets (db, auth0, stripe creds, etc) from Secret Manager"
SECRET_NAME="$SECRET_NAME_PREFIX-$CAPI_ENV"
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
docker pull us-central1-docker.pkg.dev/neat-airport-407301/lum-docker-images/lumino-api:latest
echo "Starting services with docker-compose"
docker compose up -d $COMPOSE_OPTS

echo "API services started successfully"
