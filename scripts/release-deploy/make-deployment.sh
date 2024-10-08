#!/bin/bash

# This script is used to orchestrate the deployment process

# Import common functions and variables
source ./scripts/utils.sh

gcloud compute ssh $BUILD_VM --project=$PROJECT_ID --zone=$WORK_ZONE \
      --command="/$SERVICE_NAME/scripts/release-deploy/_git-pull.sh"
gcloud compute ssh $BUILD_VM --project=$PROJECT_ID --zone=$WORK_ZONE \
      --command="/$SERVICE_NAME/scripts/release-deploy/_build-docker-image.sh"