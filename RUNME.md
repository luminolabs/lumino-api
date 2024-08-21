# Running the API locally

### Prerequisites

1. Create a new virtual environment
2. Install the required packages:
```bash
pip install -Ur requirements.txt
```
3. Create a `.env` file in the root directory with the following environment variables:
```bash
CAPI_ENV=local
CAPI_DB_NAME=lumino_api
CAPI_DB_USER=user123
CAPI_DB_PASS=pass123
CAPI_DB_HOST=localhost
CAPI_DB_PORT=5432
```
4. Start docker compose:
```bash
docker compose up -d
```