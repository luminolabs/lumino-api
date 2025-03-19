terraform {
  required_providers {
    google = {
      source  = "hashicorp/google-beta"
    }
  }
}

provider "google" {
  project = var.project_id
}

locals {
  version = trimsuffix(replace(file("${path.module}/../VERSION"), ".", "-"), "\n")
}

terraform {
  backend "gcs" {
    bucket = "lum-terraform-state"
    prefix = "lumino-api"
  }
}
