from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from datetime import datetime
from .base import Base

class UsageEvent(Base):
    __tablename__ = "usage_events"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    idempotency_key = Column(String(255), nullable=False, unique=True, index=True)
    usage_type = Column(String(50), nullable=False)
    quantity = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('ix_tenant_timestamp', 'tenant_id', 'timestamp'),
    )