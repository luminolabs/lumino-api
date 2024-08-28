from sqlalchemy import Column, JSON, UUID, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class FineTuningJobDetail(Base):
    """
    Represents detailed information for a fine-tuning job.

    Attributes:
        fine_tuning_job_id (UUID): The ID of the associated fine-tuning job.
        parameters (JSON): The parameters used for the fine-tuning job.
        metrics (JSON): The metrics collected during the fine-tuning process.

    Relationships:
        fine_tuning_job (FineTuningJob): The fine-tuning job associated with these details.
    """
    __tablename__ = "fine_tuning_job_details"

    # Columns
    fine_tuning_job_id = Column(UUID, ForeignKey("fine_tuning_jobs.id"), primary_key=True)
    parameters = Column(JSON, nullable=False)  # Stores job parameters as JSON
    metrics = Column(JSON, nullable=True)  # Stores job metrics as JSON

    # Relationships
    fine_tuning_job = relationship("FineTuningJob", back_populates="details", uselist=False)

    def __repr__(self) -> str:
        return f"<FineTuningJobDetail(fine_tuning_job_id={self.fine_tuning_job_id})>"