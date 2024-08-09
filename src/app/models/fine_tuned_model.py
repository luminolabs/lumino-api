from sqlalchemy import Column, String, DateTime, UUID, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class FineTunedModel(Base):
    """
    Represents a fine-tuned language model.
    """
    __tablename__ = "fine_tuned_models"

    id = Column(UUID, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), index=True)
    fine_tuning_job_id = Column(UUID, ForeignKey("fine_tuning_jobs.id"), index=True)
    description = Column(String)
    artifacts = Column(JSON)  # Stores information about model artifacts

    # Relationships
    user = relationship("User", back_populates="fine_tuned_models")
    fine_tuning_job = relationship("FineTuningJob", back_populates="fine_tuned_model")
    inference_endpoints = relationship("InferenceEndpoint", back_populates="fine_tuned_model")

    def __repr__(self) -> str:
        return f"<FineTunedModel(id={self.id}, user_id={self.user_id}, fine_tuning_job_id={self.fine_tuning_job_id})>"
