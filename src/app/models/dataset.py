from sqlalchemy import Column, String, DateTime, UUID, BigInteger, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Dataset(Base):
    """
    Represents a dataset used for fine-tuning language models.
    """
    __tablename__ = "datasets"

    id = Column(UUID, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), index=True)
    status = Column(String(50))
    description = Column(String)
    storage_url = Column(String(255))  # URL to the stored dataset file
    file_size = Column(BigInteger)  # Size of the dataset file in bytes
    errors = Column(JSON)  # Any errors encountered during processing

    # Relationships
    user = relationship("User", back_populates="datasets")
    fine_tuning_jobs = relationship("FineTuningJob", back_populates="dataset")

    def __repr__(self) -> str:
        return f"<Dataset(id={self.id}, user_id={self.user_id}, status={self.status})>"
