resource "google_compute_instance_template" "lumino_api" {
  project      = var.project_id
  machine_type = "e2-standard-4"

  # Be sure to update X in the lumino-api-tpl-X name when you update the template
  # This is because the template is in use by the MIG
  # and the only way to swap out the template is to create a new one
  # Terraform will delete the old template and create a new one with the new name
  name         = "lumino-api-tpl-2"

  disk {
    source_image = "projects/${var.resources_project_id}/global/images/lumino-api-image"
    auto_delete  = true
    boot         = true
    device_name  = "lumino-api-disk"
    mode         = "READ_WRITE"
    disk_size_gb = 50
    disk_type    = "pd-balanced"
  }

  network_interface {
    network    = "projects/${var.project_id}/global/networks/default"
    stack_type = "IPV4_ONLY"
    access_config {
      network_tier = "PREMIUM"
    }
  }

  service_account {
    email = google_service_account.lumino_api.email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  metadata = {
    startup-script = "/lumino-api/scripts/mig-runtime/start-services.sh lumino-api api"
    CAPI_ENV = var.environment
  }

  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
    provisioning_model  = "STANDARD"
    preemptible         = false
  }

  shielded_instance_config {
    enable_secure_boot          = false
    enable_vtpm                 = false
    enable_integrity_monitoring = false
  }

  reservation_affinity {
    type = "ANY_RESERVATION"
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = ["lumino-api-web"]
}

resource "google_compute_firewall" "lumino_api" {
  name    = "lumino-api-firewall"
  network = "projects/${var.project_id}/global/networks/default"

  allow {
    protocol = "tcp"
    ports    = [var.api_internal_port]
  }

  source_ranges = ["35.191.0.0/16", "130.211.0.0/22", "209.85.152.0/22", "209.85.204.0/22"]

  target_tags = ["lumino-api-web"]
}