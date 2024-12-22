resource "google_secret_manager_secret" "lumino_api_config" {
  secret_id = "lumino-api-config"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "config" {
  secret = google_secret_manager_secret.lumino_api_config.id
  secret_data = file("${path.module}/${var.environment}-config.env")
}