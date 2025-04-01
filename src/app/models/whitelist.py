from sqlalchemy import Column, String, DateTime, UUID, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Whitelist(Base):
    """
    Represents a whitelist request from a user.

    Attributes:
        id (UUID): The unique identifier for the whitelist request.
        created_at (DateTime): The timestamp when the whitelist request was created.
        updated_at (DateTime): The timestamp when the whitelist request was last updated.
        user_id (UUID): The ID of the user who made the whitelist request.
        name (str): The name provided in the whitelist request.
        email (str): The email provided in the whitelist request.
        phone_number (str): The phone number provided in the whitelist request.
        is_whitelisted (Boolean): Whether the user is whitelisted or not.
        has_signed_nda (Boolean): Whether the user has signed the NDA or not.

    Relationships:
        user (User): The user who made the whitelist request.
    """
    __tablename__ = "whitelist"

    # Columns
    id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=False)
    is_whitelisted = Column(Boolean, default=False, nullable=False)
    has_signed_nda = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="whitelist_request")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_whitelist_user_id'),
    )

    def __repr__(self) -> str:
        return f"<Whitelist(id={self.id}, user_id={self.user_id}, name={self.name}, " \
               f"is_whitelisted={self.is_whitelisted}, has_signed_nda={self.has_signed_nda})>"