from sqlalchemy import Column, String, DateTime, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """
    Represents a user in the system.
    """
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    status = Column(String(50))
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # Relationships
    datasets = relationship("Dataset", back_populates="user")
    fine_tuning_jobs = relationship("FineTuningJob", back_populates="user")
    fine_tuned_models = relationship("FineTunedModel", back_populates="user")
    inference_endpoints = relationship("InferenceEndpoint", back_populates="user")
    api_keys = relationship("ApiKey", back_populates="user")
    usage_records = relationship("Usage", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, email={self.email})>"
