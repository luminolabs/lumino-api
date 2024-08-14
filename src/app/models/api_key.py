from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ApiKey(Base):
    """
    Represents an API key used for authentication.
    """
    __tablename__ = "api_keys"

    id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime)
    user_id = Column(UUID, ForeignKey("users.id"), index=True)
    status = Column(String(50))
    name = Column(String(255))
    prefix = Column(String(8), unique=True, index=True)
    hashed_key = Column(String(255), nullable=False)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_api_key_user_id_name'),
    )

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, user_id={self.user_id}, name={self.name}, status={self.status})>"
