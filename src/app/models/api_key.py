from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.constants import ApiKeyStatus
from app.core.cryptography import verify_password
from app.database import Base


class ApiKey(Base):
    """
    Represents an API key that can be used to authenticate requests.

    Attributes:
        id (UUID): The unique identifier for the API key.
        created_at (DateTime): The timestamp when the API key was created.
        last_used_at (DateTime | None): The timestamp when the API key was last used.
        expires_at (DateTime): The timestamp when the API key expires.
        user_id (UUID): The ID of the user who owns this API key.
        status (ApiKeyStatus): The current status of the API key.
        name (str): The name of the API key.
        prefix (str): The prefix of the API key.
        key_hash (str): The hashed API key.

    Relationships:
        user (User): The user who owns this API key.
    """
    __tablename__ = "api_keys"

    # Columns
    id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), index=True)
    status = Column(Enum(ApiKeyStatus), nullable=False, default=ApiKeyStatus.ACTIVE)
    name = Column(String(255), nullable=False)
    prefix = Column(String(8), unique=True, index=True)
    key_hash = Column(String(255), nullable=False)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    # Indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_api_key_user_id_name'),
    )

    def verify_key(self, api_key: str) -> bool:
        """
        Verify the provided API key against the stored hashed key.

        Args:
            api_key (str): The API key to verify.
        Returns:
            bool: True if the key is valid, False otherwise.
        """
        return verify_password(api_key, self.key_hash)

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, user_id={self.user_id}, name={self.name}, status={self.status})>"
