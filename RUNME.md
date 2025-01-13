### Running the API locally with Docker Compose

1. Create a `.env` file in the root directory with the following environment variables:
```bash
CAPI_ENV=local
CAPI_DB_NAME=lumino_api
CAPI_DB_USER=user123
CAPI_DB_PASS=pass123
CAPI_DB_HOST=localhost
CAPI_DB_PORT=35100
CAPI_APP_SECRET_KEY=ALongRandomlyGeneratedString%
CAPI_AUTH0_CLIENT_ID=
CAPI_AUTH0_CLIENT_SECRET=
CAPI_AUTH0_DOMAIN=
CAPI_STRIPE_SECRET_KEY=
CAPI_STRIPE_WEBHOOK_SECRET=
```
Get the `CAPI_AUTH0_*` values from 1password. Look for `Auth0 creds`.

2. Download and add the gcp credentials file to the `./secrets` directory. The file should be named `gcp_key.json`.
- Go [here](https://console.cloud.google.com/iam-admin/serviceaccounts/details/111353529676962196957/keys?project=neat-airport-407301)
- Click on the `Add key` -> `Create new key` -> `JSON` -> `Create`
- Move the downloaded file to the `./secrets` directory and rename it to `gcp_key.json`

3. Start docker compose:
```bash
docker compose up -d --build
```

4. Connect to the database and add this record to the `base_models` table:
```sql
INSERT INTO base_models (name, description, hf_url, status, meta, cluster_config)
VALUES ('llm_llama3_1_8b',
        'The Llama 3.1 8B model',
        'meta-llama/Llama-3.1-8B-Instruct',
        'ACTIVE',
        NULL,
        '{"lora":
            {"gpu_type": "a100-40gb", "num_gpus": 1},
            "qlora":
            {"gpu_type": "a100-40gb", "num_gpus": 1},
            "full":
            {"gpu_type": "a100-40gb", "num_gpus": 4}}');
INSERT INTO base_models (name, description, hf_url, status, meta, cluster_config)
VALUES ('llm_llama3_1_70b',
        'The Llama 3.1 70B model',
        'meta-llama/Llama-3.1-70B-Instruct',
        'ACTIVE',
        NULL,
        '{"lora":
        {"gpu_type": "a100-80gb", "num_gpus": 4},
          "qlora":
          {"gpu_type": "a100-80gb", "num_gpus": 4},
          "full":
          {"gpu_type": "h100-80gb", "num_gpus": 8}}');
INSERT INTO base_models (name, description, hf_url, status, meta, cluster_config)
VALUES ('llm_llama3_2_1b',
        'The Llama 3.2 1B model',
        'meta-llama/Llama-3.2-1B-Instruct',
        'ACTIVE',
        NULL,
        '{"lora":
            {"gpu_type": "a100-40gb", "num_gpus": 1},
            "qlora":
            {"gpu_type": "a100-40gb", "num_gpus": 1},
            "full":
            {"gpu_type": "a100-40gb", "num_gpus": 1}}');
INSERT INTO base_models (name, description, hf_url, status, meta, cluster_config)
VALUES ('llm_llama3_2_3b',
        'The Llama 3.2 3B model',
        'meta-llama/Llama-3.2-3B-Instruct',
        'ACTIVE',
        NULL,
        '{"lora":
            {"gpu_type": "a100-40gb", "num_gpus": 1},
            "qlora":
            {"gpu_type": "a100-40gb", "num_gpus": 1},
            "full":
            {"gpu_type": "a100-40gb", "num_gpus": 1}}');
INSERT INTO base_models (name, description, hf_url, status, meta, cluster_config)
VALUES ('llm_llama3_3_70b',
        'The Llama 3.3 70B model',
        'meta-llama/Llama-3.3-70B-Instruct',
        'ACTIVE',
        NULL,
        '{"lora":
        {"gpu_type": "a100-80gb", "num_gpus": 4},
          "qlora":
          {"gpu_type": "a100-80gb", "num_gpus": 4},
          "full":
          {"gpu_type": "h100-80gb", "num_gpus": 8}}');
INSERT INTO base_models (name, description, hf_url, status, meta, cluster_config)
VALUES ('llm_dummy',
        'Dummy model run',
        '',
        'ACTIVE',
        NULL,
        '{"lora":
            {"gpu_type": "v100", "num_gpus": 1},
            "qlora":
            {"gpu_type": "v100", "num_gpus": 1},
            "full":
            {"gpu_type": "v100", "num_gpus": 4}}');
```

5. To access the UI and generate API keys, navigate to `http://localhost:5100/` in your browser.

6. To access the API, set the `api_key` in Postman's environment variables to the value generated in the UI.

7. To enable Stripe payments locally:
```
Populate `CAPI_STRIPE_SECRET_KEY` and `CAPI_STRIPE_WEBHOOK_SECRET` in the `.env` file with the values from 1password. Look for `Stripe creds`.
brew install stripe/stripe-cli/stripe
stripe login
stripe listen --forward-to localhost:5100/v1/billing/stripe-success-callback
```