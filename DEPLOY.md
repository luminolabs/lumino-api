# Deployment Guide

## Prerequisites

The deployment process runs certain steps on the Scheduler VM. To ensure everything runs smoothly, follow these steps:

```bash
gcloud compute ssh --zone "us-central1-a" "scheduler-zen"
```

- ssh into the Scheduler VM and:
    - Paste your private GitHub SSH key to the VM under `~/.ssh/id_rsa`.
    - Make sure the private key is password protected; if not, you can add a password by running `ssh-keygen -p -f ~/.ssh/id_rsa`.
    - Make sure the private key has the correct permissions by running `chmod 600 ~/.ssh/id_rsa`.
    - Add your public SSH key to the VM under `~/.ssh/authorized_keys`.
    - Make sure your user on the VM is in the `builders` & `docker` groups (reach out if you need help).
    - Make sure to run `gcloud auth configure-docker us-central1-docker.pkg.dev` on the VM to authenticate with the Artifact Registry.
- Make sure to have the following roles on the GCP projects:
    - Under the neat-airport project:
        - Project IAM Admin
        - Artifact Registry Administrator
    - Under the deployment projects (ex: eng-ai-dev):
        - Project IAM Admin
        - Secret Manager Secret Accessor

## Building the Docker Image
In your terminal, navigate to the root directory of this project and run the following command:
```bash
./scripts/release-deploy/make-deployment.sh dev
```
This will ssh into the Scheduler VM, pull the latest code, and build and push the Docker image to the GCP artifact registry.

## Deploying the Docker Image to the MIG
In your terminal, navigate to the root directory of this project and run the following command:
```bash
./scripts/release-deploy/deploy-to-mig.sh {env}
```
This will trigger a rolling update on the MIG to replace the current VMs.
New VMs will be created and will run the latest Docker image.

### Monitor the rolling update
To monitor the rolling update, go to the [Google Cloud Console](https://console.cloud.google.com/compute/instanceGroups/details/us-central1-a/lumino-api-{env})

### Deploy a Specific Version
To deploy a specific version of the Docker image, update the `VERSION` file with the desired version number and run the following command:
```bash
./scripts/release-deploy/deploy-to-mig.sh
```
This will tag the Docker image with the specified version to `latest` and kick off the MIG rolling update as usual.