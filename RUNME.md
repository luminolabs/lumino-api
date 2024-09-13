### Running the API locally with Docker Compose

1. Create a `.env` file in the root directory with the following environment variables:
```bash
CAPI_ENV=local
CAPI_DB_NAME=lumino_api
CAPI_DB_USER=user123
CAPI_DB_PASS=pass123
CAPI_DB_HOST=localhost
CAPI_DB_PORT=35100
CAPI_AUTH0_CLIENT_ID=
CAPI_AUTH0_CLIENT_SECRET=
CAPI_AUTH0_DOMAIN=
CAPI_APP_SECRET_KEY=ALongRandomlyGeneratedString%
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
VALUES (
    'llama-3-1-8b',
    'The Llama 3.1 8B model',
    'meta-llama/Meta-Llama-3.1-8B-Instruct',
    'ACTIVE',
    NULL,
    '{"lora": 
       {"gpu_type": "a100-40gb", "num_gpus": 1}, 
      "qlora": 
       {"gpu_type": "a100-40gb", "num_gpus": 1}, 
      "full": 
       {"gpu_type": "a100-80gb", "num_gpus": 2}}'
);
```

5. To access the UI and generate API keys, navigate to `http://localhost:5100/` in your browser.

6. To access the API, set the `api_key` in Postman's environment variables to the value generated in the UI.