from sqlalchemy import Column, String, DateTime, UUID, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class FineTunedModel(Base):
    """
    Represents a fine-tuned language model.
    """
    __tablename__ = "fine_tuned_models"

    id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    fine_tuning_job_id = Column(UUID, ForeignKey("fine_tuning_jobs.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String)
    artifacts = Column(JSON)  # Stores information about model artifacts

    # Relationships
    user = relationship("User", back_populates="fine_tuned_models")
    fine_tuning_job = relationship("FineTuningJob", back_populates="fine_tuned_model")
    inference_endpoints = relationship("InferenceEndpoint", back_populates="fine_tuned_model")

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_fine_tuned_model_user_id_name'),
    )

    def __repr__(self) -> str:
        return f"<FineTunedModel(id={self.id}, name={self.name}, user_id={self.user_id}, fine_tuning_job_id={self.fine_tuning_job_id})>"
