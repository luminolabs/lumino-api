from uuid import uuid4
from sqlalchemy import Column, String, DateTime, UUID, Index, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.constants import UserStatus
from app.core.database import Base


class User(Base):
    """
    Represents a user in the system.

    Attributes:
        id (UUID): The unique identifier for the user.
        created_at (DateTime): The timestamp when the user was created.
        updated_at (DateTime): The timestamp when the user was last updated.
        status (UserStatus): The current status of the user.
        name (str): The name of the user.
        email (str): The email address of the user.
        password_hash (str): The hashed password of the user.

    Relationships:
        datasets (List[Dataset]): The datasets created by the user.
        fine_tuning_jobs (List[FineTuningJob]): The fine-tuning jobs created by the user.
        fine_tuned_models (List[FineTunedModel]): The fine-tuned models created by the user.
        api_keys (List[ApiKey]): The API keys owned by the user.
        usage_records (List[Usage]): The usage records for the user
    """
    __tablename__ = "users"

    # Columns
    id = Column(UUID, primary_key=True, default=uuid4, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.ACTIVE)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)

    # Relationships
    datasets = relationship("Dataset", back_populates="user")
    fine_tuning_jobs = relationship("FineTuningJob", back_populates="user")
    fine_tuned_models = relationship("FineTunedModel", back_populates="user")
    api_keys = relationship("ApiKey", back_populates="user")
    usage_records = relationship("Usage", back_populates="user")

    # Indexes
    __table_args__ = (
        Index('idx_users_email', email, unique=True),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, email={self.email})>"
