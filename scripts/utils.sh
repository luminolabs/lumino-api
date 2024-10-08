PROJECT_ID="neat-airport-407301"
ARTIFACT_REPO_URL="us-central1-docker.pkg.dev/neat-airport-407301/lum-docker-images"
WORK_ZONE="us-central1-a"
BUILD_VM="scheduler-zen"

# Exit on errors
set -e

# Setup the environment
LOCAL_ENV="local"
if [[ "$CAPI_ENV" == "" ]]; then
  CAPI_ENV="$LOCAL_ENV"
fi

if [[ "$CAPI_ENV" != "$LOCAL_ENV" ]]; then
  # Change to the directory where the Dockerfile is located
  cd /$SERVICE_NAME

  # Export .env environment variables; note, we aren't aware of which environment
  # we're running on before importing CAPI_ENV from .env,
  # so we can't cd to /pipeline-zen-jobs conditionally above
  eval $(cat ./.env | grep -v '^#' | tr -d '\r')
  echo "CAPI_ENV set to $CAPI_ENV"
fi