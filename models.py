from sqlalchemy import Column, Integer, String, Boolean, DateTime
from database import Base
from datetime import datetime

class AccessRequest(Base):
    __tablename__ = "access_requests"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    code = Column(String, nullable=True)
    request_status = Column(String, default="pending")  # pending, approved, rejected
    code_expires_at = Column(DateTime, nullable=True)
    access_expires_at = Column(DateTime, nullable=True)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)

