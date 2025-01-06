# Deployment Guide

## Prerequisites
ssh into the Scheduler VM and paste your private GitHub SSH key to the VM under `~/.ssh/id_rsa`.
- Make sure the key is password protected; if not, you can add a password by running `ssh-keygen -p -f ~/.ssh/id_rsa`.
- Make sure the key has the correct permissions by running `chmod 600 ~/.ssh/id_rsa`.  
```bash
gcloud compute ssh --zone "us-central1-a" "scheduler-zen"
```
This will allow pulling from our private GitHub repository during the deployment process.

## Update VERSION file
Make sure the `VERSION` file is updated with the new version number. This version number will be used to tag the Docker image and name the VM template.

## Building the Docker Image
In your terminal, navigate to the root directory of this project and run the following command:
```bash
./scripts/release-deploy/make-deployment.sh
```
This will ssh into the Scheduler VM, pull the latest code, and build and push the Docker image to the GCP artifact registry.

## Deploying the Docker Image to the MIG
In your terminal, navigate to the root directory of this project and run the following command:
```bash
./scripts/release-deploy/deploy-to-mig.sh
```
This will trigger a rolling update on the MIG to replace the current VMs. 
New VMs will be created and will run the latest Docker image.

### Monitor the rolling update
To monitor the rolling update, go to the [Google Cloud Console](https://console.cloud.google.com/compute/instanceGroups/details/us-central1-a/lumino-api-prod)

### Deploy a Specific Version
To deploy a specific version of the Docker image, update the `VERSION` file with the desired version number and run the following command:
```bash
./scripts/release-deploy/deploy-to-mig.sh
```
This will tag the Docker image with the specified version to `latest` and kick off the MIG rolling update as usual.