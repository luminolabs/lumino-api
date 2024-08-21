from sqlalchemy import Column, String, DateTime, UUID, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class FineTunedModel(Base):
    """
    Represents a fine-tuned language model.

    Attributes:
        id (UUID): The unique identifier for the fine-tuned model.
        created_at (DateTime): The timestamp when the fine-tuned model was created.
        user_id (UUID): The ID of the user who created this fine-tuned model.
        fine_tuning_job_id (UUID): The ID of the fine-tuning job that created this model.
        name (str): The name of the fine-tuned model.
        description (str): A description of the fine-tuned model.
        artifacts (JSON): Information about model artifacts, stored as JSON.

    Relationships:
        user (User): The user who created this fine-tuned model.
        fine_tuning_job (FineTuningJob): The fine-tuning job that created this model.
    """
    __tablename__ = "fine_tuned_models"

    # Columns
    id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    fine_tuning_job_id = Column(UUID, ForeignKey("fine_tuning_jobs.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    artifacts = Column(JSON, nullable=False)

    # Relationships
    user = relationship("User", back_populates="fine_tuned_models")
    fine_tuning_job = relationship("FineTuningJob", back_populates="fine_tuned_model")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_fine_tuned_model_user_id_name'),
    )

    def __repr__(self) -> str:
        return (f"<FineTunedModel(id={self.id}, name={self.name}, "
                f"user_id={self.user_id}, fine_tuning_job_id={self.fine_tuning_job_id})>")