import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, UsageEvent, Tenant, Plan
from services import MeterService
from datetime import datetime

# Test database
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Seed test data
    plan = Plan(id=1, name="Free", api_limit=1000, token_limit=100000,
                price_per_api_call=0.001, price_per_input_token=0.00001,
                price_per_cached_input_token=0.000003, price_per_output_token=0.00002)
    db.add(plan)
    db.commit()
    
    tenant = Tenant(id=1, name="Test Tenant", email="test@example.com", plan_id=1)
    db.add(tenant)
    db.commit()
    
    yield db
    db.rollback()
    Base.metadata.drop_all(bind=engine)

def test_idempotency_prevents_double_counting(db):
    """Test that same idempotency key doesn't create duplicate usage events"""
    tenant_id = 1
    idempotency_key = "test-key-123"
    
    # First request
    result1 = MeterService.record_usage(
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        usage_type="api_call",
        quantity=1,
        db=db
    )
    
    # Second request with same key
    result2 = MeterService.record_usage(
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        usage_type="api_call",
        quantity=1,
        db=db
    )
    
    # Verify only one event exists
    events = db.query(UsageEvent).filter(
        UsageEvent.idempotency_key == idempotency_key
    ).all()
    
    assert len(events) == 1
    assert result2["duplicate"] == True
    assert result1["id"] == result2["id"]

def test_quota_boundary_blocks_after_limit(db):
    """Test that quota enforcement blocks requests after limit"""
    tenant_id = 1
    from models.plan import Plan
    
    # Set low limit for testing (override in test)
    plan = db.query(Plan).filter(Plan.id == 1).first()
    plan.api_limit = 5
    db.commit()
    
    # Make 5 requests (should work)
    for i in range(5):
        result = MeterService.record_usage(
            tenant_id=tenant_id,
            idempotency_key=f"key-{i}",
            usage_type="api_call",
            quantity=1,
            db=db
        )
        assert result["duplicate"] == False
    
    # 6th request should be blocked
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as excinfo:
        MeterService.record_usage(
            tenant_id=tenant_id,
            idempotency_key="key-6",
            usage_type="api_call",
            quantity=1,
            db=db
        )
    
    assert excinfo.value.status_code == 429
    assert "quota exceeded" in str(excinfo.value.detail).lower()