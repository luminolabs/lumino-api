-- Users table
CREATE TABLE Users (
                       id UUID PRIMARY KEY,
                       created_at TIMESTAMP NOT NULL,
                       updated_at TIMESTAMP NOT NULL,
                       status VARCHAR(50),
                       name VARCHAR(255) NOT NULL,
                       email VARCHAR(255) NOT NULL,
                       password_hash VARCHAR(255) NOT NULL
);

-- BaseModels table
CREATE TABLE BaseModels (
                            id UUID PRIMARY KEY,
                            description TEXT,
                            hf_url VARCHAR(255),
                            hf_is_gated BOOLEAN,
                            status VARCHAR(50),
                            metadata JSONB
);

-- Datasets table
CREATE TABLE Datasets (
                          id UUID PRIMARY KEY,
                          created_at TIMESTAMP NOT NULL,
                          user_id UUID,
                          status VARCHAR(50),
                          description TEXT,
                          storage_url VARCHAR(255),
                          file_size BIGINT,
                          errors JSONB,
                          FOREIGN KEY (user_id) REFERENCES Users(id)
);

-- FineTuningJobs table
CREATE TABLE FineTuningJobs (
                                id UUID PRIMARY KEY,
                                created_at TIMESTAMP NOT NULL,
                                updated_at TIMESTAMP NOT NULL,
                                user_id UUID,
                                base_model_id UUID,
                                dataset_id UUID,
                                status VARCHAR(50),
                                current_step INTEGER,
                                total_steps INTEGER,
                                current_epoch INTEGER,
                                total_epochs INTEGER,
                                num_tokens BIGINT,
                                FOREIGN KEY (user_id) REFERENCES Users(id),
                                FOREIGN KEY (base_model_id) REFERENCES BaseModels(id),
                                FOREIGN KEY (dataset_id) REFERENCES Datasets(id)
);

-- FineTuningJobDetails table
CREATE TABLE FineTuningJobDetails (
                                      fine_tuning_job_id UUID PRIMARY KEY,
                                      parameters JSONB,
                                      metrics JSONB,
                                      FOREIGN KEY (fine_tuning_job_id) REFERENCES FineTuningJobs(id)
);

-- FineTunedModels table
CREATE TABLE FineTunedModels (
                                 id UUID PRIMARY KEY,
                                 created_at TIMESTAMP NOT NULL,
                                 user_id UUID,
                                 fine_tuning_job_id UUID,
                                 description TEXT,
                                 artifacts JSONB,
                                 FOREIGN KEY (user_id) REFERENCES Users(id),
                                 FOREIGN KEY (fine_tuning_job_id) REFERENCES FineTuningJobs(id)
);

-- InferenceEndpoints table
CREATE TABLE InferenceEndpoints (
                                    id UUID PRIMARY KEY,
                                    created_at TIMESTAMP NOT NULL,
                                    updated_at TIMESTAMP NOT NULL,
                                    user_id UUID,
                                    fine_tuned_model_id UUID,
                                    status VARCHAR(50),
                                    machine_type VARCHAR(50),
                                    parameters JSONB,
                                    FOREIGN KEY (user_id) REFERENCES Users(id),
                                    FOREIGN KEY (fine_tuned_model_id) REFERENCES FineTunedModels(id)
);

-- InferenceQueries table
CREATE TABLE InferenceQueries (
                                  id UUID PRIMARY KEY,
                                  created_at TIMESTAMP NOT NULL,
                                  inference_endpoint_id UUID,
                                  request TEXT,
                                  response TEXT,
                                  input_tokens INTEGER,
                                  output_tokens INTEGER,
                                  response_time NUMERIC,
                                  FOREIGN KEY (inference_endpoint_id) REFERENCES InferenceEndpoints(id)
);

-- ApiKeys table
CREATE TABLE ApiKeys (
                         id UUID PRIMARY KEY,
                         created_at TIMESTAMP NOT NULL,
                         last_used_at TIMESTAMP,
                         expires_at TIMESTAMP,
                         user_id UUID,
                         status VARCHAR(50),
                         name VARCHAR(255),
                         prefix VARCHAR(8),
                         hashed_key VARCHAR(255),
                         FOREIGN KEY (user_id) REFERENCES Users(id)
);

-- Usage table
CREATE TABLE Usage (
                       id UUID PRIMARY KEY,
                       created_at TIMESTAMP NOT NULL,
                       user_id UUID,
                       service_name VARCHAR(50),
                       service_id UUID,
                       usage_amount DECIMAL,
                       cost DECIMAL NOT NULL,
                       FOREIGN KEY (user_id) REFERENCES Users(id)
);

-- Add indexes for frequently queried columns
CREATE INDEX idx_users_email ON Users(email);
CREATE INDEX idx_datasets_user_id ON Datasets(user_id);
CREATE INDEX idx_fine_tuning_jobs_user_id ON FineTuningJobs(user_id);
CREATE INDEX idx_fine_tuned_models_user_id ON FineTunedModels(user_id);
CREATE INDEX idx_inference_endpoints_user_id ON InferenceEndpoints(user_id);
CREATE INDEX idx_api_keys_user_id ON ApiKeys(user_id);
CREATE INDEX idx_usage_user_id ON Usage(user_id);