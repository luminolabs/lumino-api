from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Usage(Base):
    """
    Represents a usage record for billing and monitoring purposes.
    """
    __tablename__ = "usage"

    id = Column(UUID, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), index=True)
    service_name = Column(String(50))
    service_id = Column(UUID)
    usage_amount = Column(Numeric(precision=18, scale=6))
    cost = Column(Numeric(precision=18, scale=6), nullable=False)

    # Relationship
    user = relationship("User", back_populates="usage_records")

    def __repr__(self) -> str:
        return f"<Usage(id={self.id}, user_id={self.user_id}, service_name={self.service_name}, cost={self.cost})>"
