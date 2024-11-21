from sqlalchemy import Column, DateTime, UUID, ForeignKey, Enum, Integer, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.constants import UsageUnit, ServiceName
from app.core.database import Base


class Usage(Base):
    """
    Represents a usage record for a service, such as fine-tuning a model.

    Attributes:
        id (UUID): The unique identifier for the usage record.
        created_at (DateTime): The timestamp when the usage record was created.
        user_id (UUID): The ID of the user who used the service.
        usage_amount (float): The amount of usage.
        usage_unit (UsageUnit): The unit of usage.
        cost (float): The cost of the usage.
        service_name (ServiceName): The name of the service.
        fine_tuning_job_id (UUID): The ID of the fine-tuning job associated with this usage record.

    Relationships:
        user (User): The user who used the service.
        fine_tuning_job (FineTuningJob): The fine-tuning job associated with this usage record.
    """
    __tablename__ = "usage"

    # Columns
    id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), index=True, nullable=False)
    usage_amount = Column(Integer, nullable=False)
    usage_unit = Column(Enum(UsageUnit), nullable=False, default=UsageUnit.TOKEN)
    cost = Column(Float, nullable=False)
    service_name = Column(Enum(ServiceName), nullable=False, default=ServiceName.FINE_TUNING_JOB)
    fine_tuning_job_id = Column(UUID, ForeignKey("fine_tuning_jobs.id"), nullable=False, unique=True)

    # Relationships
    user = relationship("User", back_populates="usage_records")
    fine_tuning_job = relationship("FineTuningJob", back_populates="usage_record", uselist=False)

    def __repr__(self) -> str:
        return f"<Usage(id={self.id}, user_id={self.user_id}, service_name={self.service_name}, cost={self.cost})>"
