from sqlalchemy import Column, String, Boolean, UUID, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class BaseModel(Base):
    """
    Represents a base language model available for fine-tuning.
    """
    __tablename__ = "base_models"

    id = Column(UUID, primary_key=True, index=True)
    description = Column(String)
    hf_url = Column(String(255))  # URL to the model on Hugging Face
    hf_is_gated = Column(Boolean)  # Whether the model is gated on Hugging Face
    status = Column(String(50))
    metadata = Column(JSON)  # Additional metadata stored as JSON

    # Relationships
    fine_tuning_jobs = relationship("FineTuningJob", back_populates="base_model")

    def __repr__(self) -> str:
        return f"<BaseModel(id={self.id}, description={self.description})>"
