# LLM Fine-tuning API

This project provides a comprehensive API for managing Large Language Model (LLM) fine-tuning processes and related resources. It allows users to upload datasets, create fine-tuning jobs, and track usage.

## Table of Contents

- [Features](#features)
- [API Structure](#api-structure)
- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Database Schema](#database-schema)

## Features

- User management and authentication
- API key management for secure access
- Dataset upload and management
- Fine-tuning job creation and monitoring
- Inference endpoint management
- Usage tracking and cost calculation
- Base model and fine-tuned model information retrieval

## API Structure

The API is divided into several modules:

1. **Users**: User account management and authentication
2. **API Keys**: Management of API keys for authentication
3. **Datasets**: Upload and management of training datasets
4. **Fine-tuning**: Creation and monitoring of fine-tuning jobs
5. **Models**: Information about base models and fine-tuned models
7. **Usage**: Tracking of resource usage and associated costs

## Authentication

The API uses bearer token authentication. Users can obtain an access token by signing up and logging in through the `/v1/users` endpoints. API keys can also be created and managed for long-term programmatic access.

## Database Schema

The project uses a PostgreSQL database with the following main tables:

- Users
- BaseModels
- Datasets
- FineTuningJobs
- FineTunedModels
- InferenceEndpoints
- InferenceQueries
- ApiKeys
- Usage