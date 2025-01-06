# Lumino API Infrastructure

This directory contains the Terraform configuration for Lumino API's cloud infrastructure on Google Cloud Platform (GCP). 

The infrastructure is designed to support scalable fine-tuning job processing with high availability and security.

## Directory Structure

```
terraform/
├── config-example.env      # Example application configuration variables template
├── db.tf                   # Database configuration
├── dev.tfvars              # Terraform variables for dev environment
├── dev-config.env          # Application configuration variables for dev environment (not version controlled)
├── lb.tf                   # Load balancer configuration
├── main.tf                 # Main Terraform configuration file
├── mig.tf                  # Managed Instance Group configuration
├── permissions.tf          # IAM permissions and roles configuration
├── README.md               # Documentation for Terraform configuration
├── secrets.tf              # Secret Manager configuration
├── secrets.tfvars          # Terraform secrets variables (not version controlled)
├── secrets-example.tfvars  # Example Terraform secrets variables template
├── template.tf             # Instance template configuration
└── variables.tf            # Variable definitions
```

## Core Components

### Load Balancer
- Defined in `lb.tf`
- External HTTPS load balancer
- SSL/TLS termination with managed certificates
- HTTP-to-HTTPS redirect
- Security policies with:
   - Rate limiting (90 requests per minute per IP)
   - Layer 7 DDoS protection
   - Custom security rules

### Managed Instance Group (MIG)
- Defined in `mig.tf`
- Autoscaling configuration:
   - Minimum 1 instance
   - Maximum 10 instances
   - CPU utilization target of 60%
- Rolling update policy for zero-downtime deployments
- Health checks via HTTP endpoint `/v1/health`
- Instance lifecycle management with automatic repair

### Database
- Defined in `db.tf`
- PostgreSQL instance on Cloud SQL
- User and database configuration
- Connection management

### Instance Templates
- Defined in `template.tf`
- Version-controlled templates using VERSION file
- Pre-configured with:
   - E2 standard machine type (e2-standard-4)
   - Network configuration
   - Service account association
   - Startup scripts
   - Disk configuration

### IAM & Permissions
- Defined in `permissions.tf`
- Custom service account for API service
- IAM roles:
   - Logging and monitoring
   - Secret access
   - Storage access
   - Resource metadata

## Design Patterns

### 1. Environment Segregation
- Separate tfvars files for different environments
- Environment-specific resource naming
- Consistent environment variable prefixes

### 2. Secret Management
Two-tiered approach:
1. Terraform Secrets (`secrets.tfvars`)
   - Database passwords
   - Other infrastructure secrets
2. Application Secrets (Secret Manager)
   - Auth0 credentials
   - API keys
   - Database connection info

### 3. Rolling Deployments
- Zero-downtime updates using MIG
- Version tracking via VERSION file
- Automatic template versioning
- Stateless application design

## Setup and Usage

### Prerequisites
1. OpenTofu installed
2. GCP project access and credentials
3. Required files:
   - `{env}-config.env` with application configuration
   - `secrets.tfvars` with infrastructure secrets
   - Environment tfvars file (e.g., `dev.tfvars`)

### Configuration Steps
1. Copy `config-example.env` to `{env}-config.env`
2. Copy `secrets-example.tfvars` to `secrets.tfvars`
3. Set required variables in both files

### Commands
```bash
# Initialize Terraform
tofu init

# Plan changes
tofu plan -var-file="{env}.tfvars" -var-file="secrets.tfvars"

# Apply changes
tofu apply -var-file="{env}.tfvars" -var-file="secrets.tfvars"
```

## Infrastructure Updates

### Version Control
1. Update VERSION file with new version
2. Build new Docker image using `make-deployment.sh`
3. Deploy using `deploy-to-mig.sh`

### Rolling Updates Process
1. New instance template created with version suffix
2. MIG updated to use new template
3. Instances replaced one at a time
4. Health checks ensure availability
5. Old template removed after successful update

## Security Considerations

### Network Security
- HTTPS-only access
- DDoS protection
- Rate limiting
- IP filtering capabilities

### Access Control
- Principle of the least privilege
- Service account with minimal permissions
- Separate roles for different components

### Secret Management
- Application secrets in Secret Manager
- Infrastructure secrets in tfvars

## Best Practices

### Making Changes
1. Test in dev environment first
2. Use meaningful commit messages
3. Follow naming conventions
4. Maintain backwards compatibility

## Monitoring and Maintenance

### Health Checks
- HTTP endpoint monitoring
- Instance auto-repair
- Load balancer health probes

### Logging
- Cloud Logging integration
- Load balancer logging
- Application logs