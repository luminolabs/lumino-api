from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.constants import ApiKeyStatus
from app.core.security import verify_password
from app.database import Base


class ApiKey(Base):
    """
    Represents an API key that can be used to authenticate requests
    """
    __tablename__ = "api_keys"

    id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime)
    user_id = Column(UUID, ForeignKey("users.id"), index=True)
    status = Column(Enum(ApiKeyStatus), nullable=False, default=ApiKeyStatus.ACTIVE)
    name = Column(String(255))
    prefix = Column(String(8), unique=True, index=True)
    hashed_key = Column(String(255), nullable=False)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_api_key_user_id_name'),
    )

    def verify_key(self, api_key: str) -> bool:
        return verify_password(api_key, self.hashed_key)

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, user_id={self.user_id}, name={self.name}, status={self.status})>"
