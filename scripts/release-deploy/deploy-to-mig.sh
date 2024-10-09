#!/bin/bash

# This script is used to restart the service on the MIG VMs, after make-deployment.sh has been run
# Run this script locally, after make-deployment.sh has been run

# Import common functions and variables
source ./scripts/utils.sh  # Sets $SERVICE_NAME

echo "About to delete instances in the MIG group: $SERVICE_NAME-prod. Instances will be recreated automatically."

# Get the list of MIG VMs
VMS=$(gcloud compute instance-groups managed list-instances $SERVICE_NAME-prod \
  --project=$PROJECT_ID --zone=$WORK_ZONE \
  --filter="instanceStatus=RUNNING AND currentAction=NONE" \
  --format="value(name)")

# Loop through each VM
for VM in $VMS; do
    echo "Deleting VM: $VM"
    gcloud compute instance-groups managed delete-instances $SERVICE_NAME-prod \
      --project=$PROJECT_ID --zone=$WORK_ZONE \
      --instances=$VM --quiet || true
    echo "Completed deleting VM: $VM"
done

echo "Done."