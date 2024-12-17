resource "google_service_account" "lumino_api" {
  account_id   = "lumino-api-sa"
  display_name = "Lumino API Service Account"
  description  = "Service account for running the Lumino API"
  project      = var.project_id
}

resource "google_project_iam_member" "lumino_api_project" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/secretmanager.secretAccessor",
    "roles/secretmanager.viewer",
    "roles/opsconfigmonitoring.resourceMetadata.writer",
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.lumino_api.email}"
}

resource "google_storage_bucket_iam_member" "pipeline_zen_jobs_results" {
  for_each = toset([var.environment, "local"])

  bucket = "lum-${each.key}-pipeline-zen-datasets"
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.lumino_api.email}"
}

resource "google_artifact_registry_repository_iam_member" "lumino_api" {
  member     = "serviceAccount:${google_service_account.lumino_api.email}"
  repository = "lum-docker-images"
  project    = var.resources_project_id
  location   = var.region
  role       = "roles/artifactregistry.reader"
}