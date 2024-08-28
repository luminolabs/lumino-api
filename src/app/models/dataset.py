from sqlalchemy import Column, String, DateTime, UUID, BigInteger, JSON, ForeignKey, UniqueConstraint, Enum, event
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.constants import DatasetStatus
from app.core.database import Base


class Dataset(Base):
    """
    Represents a dataset used for fine-tuning language models.

    Attributes:
        id (UUID): The unique identifier for the dataset.
        created_at (DateTime): The timestamp when the dataset was created.
        user_id (UUID): The ID of the user who owns this dataset.
        status (DatasetStatus): The current status of the dataset.
        name (str): The name of the dataset.
        description (str | None): An optional description of the dataset.
        file_name (str): The file name of the dataset; we prefix with a timestamp and user ID to ensure uniqueness.
        file_size (int): The size of the dataset file in bytes.
        errors (dict | None): Any errors encountered during dataset processing.

    Relationships:
        user (User): The user who owns this dataset.
        fine_tuning_jobs (list[FineTuningJob]): The fine-tuning jobs using this dataset.
    """
    __tablename__ = "datasets"

    # Columns
    id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(DatasetStatus), nullable=False, default=DatasetStatus.UPLOADED)
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    file_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    errors = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="datasets")
    fine_tuning_jobs = relationship("FineTuningJob", back_populates="dataset")

    # Indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_dataset_user_id_name'),
    )

    def __repr__(self) -> str:
        return f"<Dataset(id={self.id}, name={self.name}, user_id={self.user_id}, status={self.status})>"
