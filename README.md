# Lumino API

Lumino API is a powerful solution for fine-tuning, deploying, and interacting with Large Language Models (LLMs). This API focuses on providing advanced capabilities for model customization and inference, along with comprehensive dataset and model management features.

## Key Features

1. **Fine-tuning and Inference**
   - Create and manage fine-tuning jobs for customizing LLMs
   - Deploy fine-tuned models as inference endpoints
   - Interact with deployed models via API for real-time inference

2. **Dataset and Model Management**
   - Upload, list, and manage datasets for fine-tuning
   - Access detailed information about available LLM models
   - Track and manage your custom models

3. **Additional Features**
   - User management and authentication
   - API key management for secure access
   - Billing and usage tracking

## Getting Started

To start using the Lumino API for fine-tuning and inference, follow these steps:

1. **Sign Up**: Create an account using the `/users` endpoint.
2. **Authentication**: Obtain an access token by logging in via `/users/login`.
3. **API Keys**: Generate an API key using the `/api-keys` endpoint for secure access.
4. **Upload Dataset**: Use the `/datasets` endpoint to upload your training data.
5. **Create Fine-tuning Job**: Initiate a fine-tuning job with the `/fine-tuning-jobs` endpoint.
6. **Deploy Model**: Once fine-tuning is complete, deploy your model using the `/inference-endpoints` endpoint.
7. **Run Inference**: Send prompts to your deployed model for real-time inference.

## Core API Endpoints

The Lumino API is organized into several modules, with a focus on fine-tuning and inference:

- `/fine-tuning-jobs`: Create and manage fine-tuning jobs
  - POST /fine-tuning-jobs: Create a new fine-tuning job
  - GET /fine-tuning-jobs: List all fine-tuning jobs
  - GET /fine-tuning-jobs/{job_id}: Get details of a specific job
  - GET /fine-tuning-jobs/{job_id}/results: Retrieve results of a completed job

- `/inference-endpoints`: Deploy and interact with fine-tuned models
  - POST /inference-endpoints: Create a new inference endpoint
  - GET /inference-endpoints: List all inference endpoints
  - POST /inference-endpoints/{endpoint_id}/prompts: Send a prompt to the model
  - GET /inference-endpoints/{endpoint_id}/prompts: Retrieve conversation history

- `/datasets`: Manage datasets for fine-tuning
  - POST /datasets: Upload a new dataset file
  - GET /datasets: List all uploaded datasets
  - GET /datasets/{dataset_id}: Get information about a specific dataset

- `/models`: Access information about available LLM models
  - GET /models: List all available LLM models
  - GET /models/{model_name}: Get detailed information about a specific model

Additional endpoints are available for user management, API key handling, and billing information.

## Authentication

Most endpoints require authentication. Use the Bearer token obtained from the login endpoint in the `Authorization` header:

```
Authorization: Bearer <your_access_token>
```

