from sqlalchemy import Column, String, DateTime, UUID, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class InferenceEndpoint(Base):
    """
    Represents an inference endpoint for a fine-tuned model.
    """
    __tablename__ = "inference_endpoints"

    id = Column(UUID, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), index=True)
    fine_tuned_model_id = Column(UUID, ForeignKey("fine_tuned_models.id"), index=True)
    status = Column(String(50))
    machine_type = Column(String(50))
    parameters = Column(JSON)  # Stores endpoint configuration parameters

    # Relationships
    user = relationship("User", back_populates="inference_endpoints")
    fine_tuned_model = relationship("FineTunedModel", back_populates="inference_endpoints")
    inference_queries = relationship("InferenceQuery", back_populates="inference_endpoint")

    def __repr__(self) -> str:
        return f"<InferenceEndpoint(id={self.id}, user_id={self.user_id}, fine_tuned_model_id={self.fine_tuned_model_id}, status={self.status})>"
