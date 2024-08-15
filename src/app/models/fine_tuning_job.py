from sqlalchemy import Column, String, DateTime, UUID, Integer, BigInteger, ForeignKey, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.constants import FineTuningJobStatus
from app.database import Base


class FineTuningJob(Base):
    """
    Represents a fine-tuning job for a language model.

    Attributes:
        id (UUID): The unique identifier for the fine-tuning job.
        created_at (DateTime): The timestamp when the job was created.
        updated_at (DateTime): The timestamp when the job was last updated.
        user_id (UUID): The ID of the user who created the job.
        base_model_id (UUID): The ID of the base model used for fine-tuning.
        dataset_id (UUID): The ID of the dataset used for fine-tuning.
        status (FineTuningJobStatus): The current status of the job.
        name (str): The name of the fine-tuning job.
        current_step (int): The current step of the fine-tuning process.
        total_steps (int): The total number of steps in the fine-tuning process.
        current_epoch (int): The current epoch of the fine-tuning process.
        total_epochs (int): The total number of epochs in the fine-tuning process.
        num_tokens (int): The number of tokens processed in the fine-tuning job.
    """
    __tablename__ = "fine_tuning_jobs"

    id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    base_model_id = Column(UUID, ForeignKey("base_models.id"), nullable=False)
    dataset_id = Column(UUID, ForeignKey("datasets.id"), nullable=False)
    status = Column(Enum(FineTuningJobStatus), nullable=False, default=FineTuningJobStatus.NEW)
    name = Column(String(255), nullable=False)
    current_step = Column(Integer)
    total_steps = Column(Integer)
    current_epoch = Column(Integer)
    total_epochs = Column(Integer)
    num_tokens = Column(BigInteger)

    # Relationships
    user = relationship("User", back_populates="fine_tuning_jobs")
    base_model = relationship("BaseModel", back_populates="fine_tuning_jobs")
    dataset = relationship("Dataset", back_populates="fine_tuning_jobs")
    details = relationship("FineTuningJobDetail", back_populates="fine_tuning_job", uselist=False)
    fine_tuned_model = relationship("FineTunedModel", back_populates="fine_tuning_job", uselist=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_fine_tuning_job_user_id_name'),
    )

    def __repr__(self) -> str:
        return (f"<FineTuningJob(id={self.id}, name={self.name}, user_id={self.user_id}, "
                f"base_model_id={self.base_model_id}, status={self.status})>")