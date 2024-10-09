#!/bin/bash

# This script is used to restart the service on the MIG VMs, after make-deployment.sh has been run
# Run this script locally, after make-deployment.sh has been run

# Import common functions and variables
source ./scripts/utils.sh # Sets $SERVICE_NAME

# Get the list of MIG VMs
VMS=$(gcloud compute instance-groups managed list-instances $SERVICE_NAME-prod --project=$PROJECT_ID --zone=$WORK_ZONE --format="value(name)")

# Loop through each VM
for VM in $VMS; do
    echo "Processing VM: $VM"
    # SSH into the VM, change directory, run the script, and exit
    gcloud compute ssh $VM --project=$PROJECT_ID --zone=$WORK_ZONE \
      --command="SERVICE_NAME=$SERVICE_NAME /$SERVICE_NAME/scripts/mig-runtime/start-services.sh --force-recreate && exit"
    echo "Completed processing VM: $VM"
done

echo "Done."