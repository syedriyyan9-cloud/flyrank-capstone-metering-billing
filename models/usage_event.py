from sqlalchemy import Column, Integer, String, Float, DateTime

class UsageEvent(Base):
    __tablename__ = "usage_events"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, nullable=False)
    idempotency_key = Column(String(255), nullable=False, unique=True)
    usage_type = Column(String(50), nullable=False)  # api_call, input_token, cached_input_token, output_token, reasoning_token
    quantity = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Indexes to add later
    # __table_args__ = (Index('ix_tenant_timestamp', 'tenant_id', 'timestamp'),)