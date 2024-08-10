from sqlalchemy import Column, Text, DateTime, UUID, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class InferenceQuery(Base):
    """
    Represents an individual inference query made to an endpoint.
    """
    __tablename__ = "inference_queries"

    id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    inference_endpoint_id = Column(UUID, ForeignKey("inference_endpoints.id"), index=True)
    request = Column(Text)
    response = Column(Text)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    response_time = Column(Float)  # Response time in seconds

    # Relationship
    inference_endpoint = relationship("InferenceEndpoint", back_populates="inference_queries")

    def __repr__(self) -> str:
        return f"<InferenceQuery(id={self.id}, inference_endpoint_id={self.inference_endpoint_id}, input_tokens={self.input_tokens}, output_tokens={self.output_tokens})>"
