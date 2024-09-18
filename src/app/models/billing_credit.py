from sqlalchemy import Column, DateTime, UUID, ForeignKey, Numeric, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BillingCredit(Base):
    """
    Represents a billing credits record for a user.

    Attributes:
        id (UUID): The unique identifier for the billing credits record.
        created_at (DateTime): The timestamp when the billing credits record was created.
        user_id (UUID): The ID of the user associated with these credits.
        credits (Numeric): The amount of credits.

    Relationships:
        user (User): The user associated with these credits.
    """
    __tablename__ = "billing_credits"

    # Columns
    id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    credits = Column(Numeric(precision=12, scale=3), nullable=False)

    # Relationships
    user = relationship("User", back_populates="billing_credits")

    def __repr__(self) -> str:
        return f"<BillingCredit(id={self.id}, user_id={self.user_id}, credits={self.credits})>"
