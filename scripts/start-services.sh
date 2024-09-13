#!/bin/bash

# This script is used to start all services on dev and production environments, don't use locally

# Exit on errors
set -e

# Set variables
PROJECT_ID="neat-airport-407301"
SECRET_NAME="lumino-api-config"

# Fetch the secret
echo "Fetching secrets (db, auth0 creds, etc) from Secret Manager"
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

# Start the services using docker-compose
echo "Starting services with docker-compose"
docker compose up --build -d

echo "API services started successfully"
