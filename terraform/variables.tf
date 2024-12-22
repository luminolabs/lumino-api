variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "environment" {
  description = "The environment (e.g., dev, prod)"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "resources_project_id" {
  description = "The GCP project ID for resources"
  type        = string
  default     = "neat-airport-407301"
}

variable "api_internal_port" {
  description = "The internal port for the API"
  type        = number
  default     = 5100
}

variable "cloud_sql_instance_name" {
  description = "The name of the Cloud SQL instance"
  type        = string
  default     = "zen-db"
}

variable "zen_db_password" {
  description = "The password for the Cloud SQL lumino_api user"
  type        = string
}