from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class BlacklistedToken(Base):
    """
    Represents a token / user session that has been logged out.

    Attributes:
        token (str): The token that has been blacklisted.
        blacklisted_on (DateTime): The timestamp when the token was blacklisted.
        expires_at (DateTime): Original token expiration; used for cleanup; see `tasks/token_cleanup.py`.
    """
    __tablename__ = "blacklisted_tokens"

    # Columns
    token = Column(String, primary_key=True, index=True)
    blacklisted_on = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<BlacklistedToken(token={self.token}, blacklisted_on={self.blacklisted_on}, expires_at={self.expires_at})>"
