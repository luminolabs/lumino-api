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

2. Start docker compose:
```bash
docker compose up -d --build
```

3. To access the UI and generate API keys, navigate to `http://localhost:5100/` in your browser.

4. To access the API, set the `api_key` in Postman's environment variables to the value generated in the UI.