#!/bin/bash

# This script is used to orchestrate the deployment process
# Run this script locally, before running deploy-to-mig.sh

# Import common functions and variables
source ./scripts/utils.sh  # Sets $SERVICE_NAME

gcloud compute ssh $BUILD_VM --project=$PROJECT_ID --zone=$WORK_ZONE \
      --command="SERVICE_NAME=$SERVICE_NAME /$SERVICE_NAME/scripts/release-deploy/_git-pull.sh"
gcloud compute ssh $BUILD_VM --project=$PROJECT_ID --zone=$WORK_ZONE \
      --command="SERVICE_NAME=$SERVICE_NAME /$SERVICE_NAME/scripts/release-deploy/_make-docker-image.sh"