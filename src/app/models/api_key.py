from sqlalchemy import Column, String, DateTime, UUID, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ApiKey(Base):
    """
    Represents an API key used for authentication.
    """
    __tablename__ = "api_keys"

    id = Column(UUID, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime)
    user_id = Column(UUID, ForeignKey("users.id"), index=True)
    status = Column(String(50))
    name = Column(String(255))
    prefix = Column(String(8), unique=True, index=True)
    hashed_key = Column(String(255), nullable=False)

    # Relationship
    user = relationship("User", back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, user_id={self.user_id}, name={self.name}, status={self.status})>"
