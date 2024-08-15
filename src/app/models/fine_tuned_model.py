from sqlalchemy import Column, String, DateTime, UUID, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class FineTunedModel(Base):
    """
    Represents a fine-tuned language model.

    This model stores information about language models that have been fine-tuned
    based on a base model and a specific dataset.

    Attributes:
        id (UUID): The unique identifier for the fine-tuned model.
        created_at (DateTime): The timestamp when the fine-tuned model was created.
        user_id (UUID): The ID of the user who created this fine-tuned model.
        fine_tuning_job_id (UUID): The ID of the fine-tuning job that created this model.
        name (str): The name of the fine-tuned model.
        description (str): A description of the fine-tuned model.
        artifacts (JSON): Information about model artifacts, stored as JSON.

    Relationships:
        user (relationship): Many-to-one relationship with User.
        fine_tuning_job (relationship): Many-to-one relationship with FineTuningJob.
        inference_endpoints (relationship): One-to-many relationship with InferenceEndpoint.

    Constraints:
        uq_fine_tuned_model_user_id_name: Ensures the combination of user_id and name is unique.
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
        """
        Returns a string representation of the FineTunedModel instance.

        Returns:
            str: A string representation of the FineTunedModel.
        """
        return (f"<FineTunedModel(id={self.id}, name={self.name}, "
                f"user_id={self.user_id}, fine_tuning_job_id={self.fine_tuning_job_id})>")