from enum import Enum


# Enumeration for user account statuses
class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"  # User account is active and can be used
    INACTIVE = "INACTIVE"  # User account is deactivated and cannot be used


# Enumeration for API key statuses
class ApiKeyStatus(str, Enum):
    ACTIVE = "ACTIVE"  # API key is active and can be used for authentication
    EXPIRED = "EXPIRED"  # API key has expired and is no longer valid
    REVOKED = "REVOKED"  # API key has been manually revoked by the user or admin


# Enumeration for dataset statuses
class DatasetStatus(str, Enum):
    UPLOADED = "UPLOADED"  # Dataset has been uploaded but not yet validated
    VALIDATED = "VALIDATED"  # Dataset has been validated and is ready for use
    ERROR = "ERROR"  # There was an error processing or validating the dataset
    DELETED = "DELETED"  # Dataset has been marked as deleted


# Enumeration for fine-tuning job statuses
class FineTuningJobStatus(str, Enum):
    NEW = "NEW"  # Job has been created but not yet started
    QUEUED = "QUEUED"  # Job is queued and waiting to start
    RUNNING = "RUNNING"  # Job is currently running
    STOPPING = "STOPPING"  # Job is in the process of being stopped
    STOPPED = "STOPPED"  # Job has been stopped by the user or system
    COMPLETED = "COMPLETED"  # Job has completed successfully
    FAILED = "FAILED"  # Job has failed to complete
    DELETED = "DELETED"  # Job has been marked as deleted


# Enumeration for compute providers
class ComputeProvider(str, Enum):
    GCP = "GCP"
    LUM = "LUM"


# Enumeration for fine-tuning job types
class FineTuningJobType(str, Enum):
    FULL = "FULL"  # Full fine-tuning job
    LORA = "LORA"  # Low-resource fine-tuning job
    QLORA = "QLORA"  # Quantized low-resource fine-tuning job


# Enumeration for base model statuses
class BaseModelStatus(str, Enum):
    ACTIVE = "ACTIVE"  # Base model is available for use
    INACTIVE = "INACTIVE"  # Base model is deactivated and cannot be used
    DEPRECATED = "DEPRECATED"  # Base model is no longer supported or recommended for use


# Enumeration for fine-tuned model statuses
class FineTunedModelStatus(str, Enum):
    ACTIVE = "ACTIVE"  # Fine-tuned model is available for use
    DELETED = "DELETED"  # Fine-tuned model has been marked as deleted


class UsageUnit(str, Enum):
    """
    Enum for the unit of the available usage units.
    """
    TOKEN = "TOKEN"


class ServiceName(str, Enum):
    """
    Enum for the name of the available services.
    """
    FINE_TUNING_JOB = "FINE_TUNING_JOB"


class BillingTransactionType(str, Enum):
    """
    Enum for the type of billing transaction.
    """
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT"
    NEW_USER_CREDIT = "NEW_USER_CREDIT"
    FINE_TUNING_JOB = "FINE_TUNING_JOB"
    STRIPE_CHECKOUT = "STRIPE_CHECKOUT"
