from sqlalchemy import Column, String, UUID, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.constants import BaseModelStatus
from app.core.database import Base


class BaseModel(Base):
    """
    Represents a base language model available for fine-tuning.

    Attributes:
        id (UUID): The unique identifier for the base model.
        name (str): The name of the base model.
        description (str): A description of the base model.
        hf_url (str): The URL to the model on Hugging Face.
        status (BaseModelStatus): The current status of the base model.
        meta (JSON): Additional metadata stored as JSON.

    Relationships:
        fine_tuning_jobs (relationship): One-to-many relationship with FineTuningJob.
    """
    __tablename__ = "base_models"

    # Columns
    id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid(), nullable=False)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)
    hf_url = Column(String(255), nullable=False)
    status = Column(Enum(BaseModelStatus), nullable=False, default=BaseModelStatus.INACTIVE)
    meta = Column(JSON, nullable=True)

    # Relationships
    fine_tuning_jobs = relationship("FineTuningJob", back_populates="base_model")

    def __repr__(self) -> str:
        return f"<BaseModel(id={self.id}, name={self.name}, status={self.status})>"