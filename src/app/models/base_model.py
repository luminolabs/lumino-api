from sqlalchemy import Column, String, Boolean, UUID, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.constants import BaseModelStatus
from app.database import Base


class BaseModel(Base):
    """
    Represents a base language model available for fine-tuning.
    """
    __tablename__ = "base_models"

    id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid(), nullable=False)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(String)
    hf_url = Column(String(255))  # URL to the model on Hugging Face
    hf_is_gated = Column(Boolean)  # Whether the model is gated on Hugging Face
    status = Column(Enum(BaseModelStatus), nullable=False, default=BaseModelStatus.INACTIVE)
    meta = Column(JSON)  # Additional meta stored as JSON

    # Relationships
    fine_tuning_jobs = relationship("FineTuningJob", back_populates="base_model")

    def __repr__(self) -> str:
        return f"<BaseModel(id={self.id}, name={self.name}, description={self.description})>"
