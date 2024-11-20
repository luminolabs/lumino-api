from sqlalchemy import Column, DateTime, UUID, ForeignKey, Numeric, String, Enum, UniqueConstraint, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.constants import BillingTransactionType
from app.core.database import Base


class BillingCredit(Base):
    """
    Represents a billing credits record for a user.

    Attributes:
        id (UUID): The unique identifier for the billing credits record.
        created_at (DateTime): The timestamp when the billing credits record was created.
        user_id (UUID): The ID of the user associated with these credits.
        credits (float): The amount of credits.
        transaction_id (str): The ID of the transaction associated with these credits.
        transaction_type (BillingTransactionType): The type of transaction associated with these

    Relationships:
        user (User): The user associated with these credits.
    """
    __tablename__ = "billing_credits"

    # Columns
    id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    credits = Column(Float, nullable=False)
    transaction_id = Column(String(255), nullable=False)
    transaction_type = Column(Enum(BillingTransactionType), nullable=False)

    # Relationships
    user = relationship("User", back_populates="billing_credits")

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "transaction_id", "transaction_type",
                         name="uq_billing_credit_user_transaction"),
    )

    def __repr__(self) -> str:
        return f"<BillingCredit(id={self.id}, user_id={self.user_id}, credits={self.credits})>"
