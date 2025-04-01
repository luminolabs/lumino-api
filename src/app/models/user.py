from uuid import uuid4

from sqlalchemy import Column, String, DateTime, UUID, Index, Enum, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.constants import UserStatus
from app.core.database import Base


class User(Base):
    """
    Represents a user in the system.

    Attributes:
        id (UUID): The unique identifier for the user.
        created_at (DateTime): The timestamp when the user was created.
        updated_at (DateTime): The timestamp when the user was last updated.
        status (UserStatus): The current status of the user.
        name (str): The name of the user.
        email (str): The email address of the user.
        auth0_user_id (str): The Auth0 user ID.
        email_verified (bool): Whether the user's email is verified or not.
        is_admin (bool): Whether the user is an admin or not.
        credits_balance (float): The current credit balance of the user.

    Relationships:
        datasets (List[Dataset]): The datasets created by the user.
        fine_tuning_jobs (List[FineTuningJob]): The fine-tuning jobs created by the user.
        fine_tuned_models (List[FineTunedModel]): The fine-tuned models created by the user.
        api_keys (List[ApiKey]): The API keys owned by the user.
        usage_records (List[Usage]): The usage records for the user.
        billing_credits (List[BillingCredit]): The billing credits records for the user.
    """
    __tablename__ = "users"

    # Columns
    id = Column(UUID, primary_key=True, default=uuid4, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.ACTIVE)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    auth0_user_id = Column(String(255), nullable=False)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_payment_method_id = Column(String(255), nullable=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    credits_balance = Column(Float, nullable=False, default=0)

    # Relationships
    datasets = relationship("Dataset", back_populates="user")
    fine_tuning_jobs = relationship("FineTuningJob", back_populates="user")
    fine_tuned_models = relationship("FineTunedModel", back_populates="user")
    api_keys = relationship("ApiKey", back_populates="user")
    usage_records = relationship("Usage", back_populates="user")
    billing_credits = relationship("BillingCredit", back_populates="user")
    whitelist_request = relationship("Whitelist", back_populates="user", uselist=False)

    # Indexes
    __table_args__ = (
        Index('idx_users_email', email, unique=True),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, email={self.email}, is_admin={self.is_admin}, credits_balance={self.credits_balance})>"
