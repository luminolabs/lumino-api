-- Create enum types for statuses
CREATE TYPE userstatus AS ENUM ('ACTIVE', 'INACTIVE');
CREATE TYPE apikeystatus AS ENUM ('ACTIVE', 'EXPIRED', 'REVOKED');
CREATE TYPE datasetstatus AS ENUM ('UPLOADED', 'VALIDATED', 'ERROR');
CREATE TYPE finetuningjobstatus AS ENUM ('NEW', 'PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'STOPPED');
CREATE TYPE basemodelstatus AS ENUM ('ACTIVE', 'INACTIVE', 'DEPRECATED');
CREATE TYPE inferenceendpointstatus AS ENUM ('NEW', 'PENDING', 'RUNNING', 'DELETED', 'FAILED');

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status userstatus NOT NULL DEFAULT 'ACTIVE',
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL
);
CREATE UNIQUE INDEX idx_users_email ON users(email);

-- Base models table
CREATE TABLE base_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    description TEXT,
    hf_url VARCHAR(255),
    hf_is_gated BOOLEAN,
    status basemodelstatus,
    name VARCHAR(255) NOT NULL,
    meta JSONB
);
CREATE UNIQUE INDEX idx_base_models_name ON base_models(name);

-- Datasets table
CREATE TABLE datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id UUID NOT NULL,
    status datasetstatus,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    storage_url VARCHAR(255),
    file_size BIGINT,
    errors JSONB,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE UNIQUE INDEX idx_datasets_user_id_name ON datasets(user_id, name);

-- Fine-tuning jobs table
CREATE TABLE fine_tuning_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id UUID NOT NULL,
    base_model_id UUID NOT NULL,
    dataset_id UUID NOT NULL,
    status finetuningjobstatus,
    name VARCHAR(255) NOT NULL,
    current_step INTEGER,
    total_steps INTEGER,
    current_epoch INTEGER,
    total_epochs INTEGER,
    num_tokens BIGINT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (base_model_id) REFERENCES base_models(id),
    FOREIGN KEY (dataset_id) REFERENCES datasets(id)
);
CREATE UNIQUE INDEX idx_fine_tuning_jobs_user_id_name ON fine_tuning_jobs(user_id, name);

-- Fine-tuning job details table
CREATE TABLE fine_tuning_job_details (
    fine_tuning_job_id UUID PRIMARY KEY,
    parameters JSONB,
    metrics JSONB,
    FOREIGN KEY (fine_tuning_job_id) REFERENCES fine_tuning_jobs(id)
);

-- Fine-tuned models table
CREATE TABLE fine_tuned_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id UUID NOT NULL,
    fine_tuning_job_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    artifacts JSONB,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (fine_tuning_job_id) REFERENCES fine_tuning_jobs(id)
);
CREATE UNIQUE INDEX idx_fine_tuned_models_user_id_name ON fine_tuned_models(user_id, name);

-- Inference endpoints table
CREATE TABLE inference_endpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id UUID NOT NULL,
    fine_tuned_model_id UUID NOT NULL,
    status inferenceendpointstatus,
    name VARCHAR(255) NOT NULL,
    machine_type VARCHAR(50),
    parameters JSONB,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (fine_tuned_model_id) REFERENCES fine_tuned_models(id)
);
CREATE UNIQUE INDEX idx_inference_endpoints_user_id_name ON inference_endpoints(user_id, name);

-- Inference queries table
CREATE TABLE inference_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    inference_endpoint_id UUID NOT NULL,
    request TEXT,
    response TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    response_time NUMERIC,
    FOREIGN KEY (inference_endpoint_id) REFERENCES inference_endpoints(id)
);

-- API keys table
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    user_id UUID NOT NULL,
    status apikeystatus,
    name VARCHAR(255),
    prefix VARCHAR(8),
    hashed_key VARCHAR(255) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE UNIQUE INDEX idx_api_keys_user_id_name ON api_keys(user_id, name);

-- Usage table
CREATE TABLE usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id UUID NOT NULL,
    service_name VARCHAR(50),
    usage_amount DECIMAL,
    cost DECIMAL NOT NULL,
    fine_tuning_job_id UUID NOT NULL,
    inference_endpoint_id UUID NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (fine_tuning_job_id) REFERENCES fine_tuning_jobs(id),
    FOREIGN KEY (inference_endpoint_id) REFERENCES inference_endpoints(id)
);

-- Blacklisted tokens table
CREATE TABLE blacklisted_tokens (
    token VARCHAR(255) PRIMARY KEY,
    blacklisted_on TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX idx_blacklisted_tokens_expires_at ON blacklisted_tokens(expires_at);

-- Create indexes for frequently queried columns
CREATE INDEX idx_datasets_user_id ON datasets(user_id);
CREATE INDEX idx_fine_tuning_jobs_user_id ON fine_tuning_jobs(user_id);
CREATE INDEX idx_fine_tuned_models_user_id ON fine_tuned_models(user_id);
CREATE INDEX idx_inference_endpoints_user_id ON inference_endpoints(user_id);
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_usage_user_id ON usage(user_id);