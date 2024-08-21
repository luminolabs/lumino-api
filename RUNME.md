### Running the API locally with Docker Compose

1. Create a `.env` file in the root directory with the following environment variables:
```bash
CAPI_ENV=local
CAPI_DB_NAME=lumino_api
CAPI_DB_USER=user123
CAPI_DB_PASS=pass123
CAPI_DB_HOST=localhost
CAPI_DB_PORT=5432
```
2. Start docker compose:
```bash
docker compose up -d
```