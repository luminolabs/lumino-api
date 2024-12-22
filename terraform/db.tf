resource "google_sql_database" "default" {
  name     = "lumino_api"
  instance = var.cloud_sql_instance_name
}

resource "google_sql_user" "default" {
  name     = "lumino_api"
  instance = var.cloud_sql_instance_name
  password = var.zen_db_password
}