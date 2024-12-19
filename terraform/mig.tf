# Configure instance group manager
resource "google_compute_instance_group_manager" "lumino_api" {
  project = var.project_id
  zone    = var.zone

  name               = "lumino-api-mig"
  base_instance_name = "lumino-api-vm"
  target_size        = 1

  version {
    instance_template = google_compute_instance_template.lumino_api.id
  }

  named_port {
    name = "web"
    port = var.api_internal_port
  }

  update_policy {
    type                  = "PROACTIVE"
    minimal_action        = "REPLACE"
    max_surge_fixed       = 1
    max_unavailable_fixed = 0
    min_ready_sec         = 60
    replacement_method    = "SUBSTITUTE"
  }

  instance_lifecycle_policy {
    force_update_on_repair    = "YES"
    default_action_on_failure = "REPAIR"
  }
}

# Configure autoscaler
resource "google_compute_autoscaler" "lumino_api" {
  name   = "lumino-api-scaler"
  zone   = var.zone
  target = google_compute_instance_group_manager.lumino_api.id

  autoscaling_policy {
    max_replicas    = 10
    min_replicas    = 1
    cooldown_period = 60

    cpu_utilization {
      target            = 0.6
      predictive_method = "NONE"
    }
  }
}