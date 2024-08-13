from enum import Enum


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ApiKeyStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class DatasetStatus(str, Enum):
    UPLOADED = "uploaded"
    VALIDATED = "validated"
    ERROR = "error"


class FineTuningJobStatus(str, Enum):
    NEW = "new"
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    STOPPING = "stopping"
    STOPPED = "stopped"


class BaseModelStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


class InferenceEndpointStatus(str, Enum):
    NEW = "new"
    PENDING = "pending"
    RUNNING = "running"
    DELETED = "deleted"
    FAILED = "failed"
