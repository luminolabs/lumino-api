from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.database import Base


class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"

    token = Column(String, primary_key=True, index=True)
    blacklisted_on = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<BlacklistedToken(token={self.token}, blacklisted_on={self.blacklisted_on}, expires_at={self.expires_at})>"
