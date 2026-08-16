from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import get_db
from services import MeterService, QuotaService, CostService
from models import Tenant

router = APIRouter()


# Request/Response Models
class GenerateRequest(BaseModel):
    tenant_id: int
    idempotency_key: str
    usage_type: str  # api_call, input_token, cached_input_token, output_token, reasoning_token
    quantity: float
    input_tokens: Optional[float] = 0
    cached_input_tokens: Optional[float] = 0
    output_tokens: Optional[float] = 0
    reasoning_tokens: Optional[float] = 0

class GenerateResponse(BaseModel):
    usage_id: int
    tenant_id: int
    usage_type: str
    quantity: float
    cost: float
    timestamp: str
    duplicate: bool
    message: str

class UsageResponse(BaseModel):
    tenant_id: int
    plan_name: str
    usage: dict
    cost_breakdown: Optional[dict] = None

@router.post("/api/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest, db: Session = Depends(get_db)):
    """
    Dummy billable endpoint that records usage.
    
    Supports idempotency via idempotency_key.
    """
    # Validate tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == request.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Handle token usage breakdown (if multiple token types in one request)
    if request.usage_type == "token_bundle":
        # Record each token type separately with same idempotency key
        # For simplicity, we'll aggregate
        total_tokens = (request.input_tokens + request.cached_input_tokens + 
                       request.output_tokens + request.reasoning_tokens)
        
        # Calculate total cost using CostService
        cost_breakdown = CostService.get_token_cost(
            request.input_tokens,
            request.cached_input_tokens,
            request.output_tokens,
            request.reasoning_tokens,
            tenant.plan_id
        )
        
        # Record as a single usage event
        result = MeterService.record_usage(
            tenant_id=request.tenant_id,
            idempotency_key=request.idempotency_key,
            usage_type="token_bundle",
            quantity=total_tokens,
            db=db
        )
        
        return GenerateResponse(
            usage_id=result["id"],
            tenant_id=result["tenant_id"],
            usage_type=request.usage_type,
            quantity=result["quantity"],
            cost=result["cost"],
            timestamp=result["timestamp"],
            duplicate=result["duplicate"],
            message=f"Recorded {total_tokens} tokens. Cost: ${cost_breakdown['total_cost']:.6f}"
        )
    
    # Single usage type
    result = MeterService.record_usage(
        tenant_id=request.tenant_id,
        idempotency_key=request.idempotency_key,
        usage_type=request.usage_type,
        quantity=request.quantity,
        db=db
    )
    
    return GenerateResponse(
        usage_id=result["id"],
        tenant_id=result["tenant_id"],
        usage_type=result["usage_type"],
        quantity=result["quantity"],
        cost=result["cost"],
        timestamp=result["timestamp"],
        duplicate=result["duplicate"],
        message=result["message"]
    )

@router.get("/api/usage")
def get_usage(tenant_id: int, db: Session = Depends(get_db)):
    """Get usage summary for a tenant"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get usage summary
    usage_summary = MeterService.get_usage_summary(tenant_id, db)
    
    # Get quota status
    quota = QuotaService.check_quota(tenant_id, db)
    
    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant.name,
        "plan_name": usage_summary["plan_name"],
        "usage": usage_summary["usage"],
        "quota_status": quota,
        "message": f"Used {quota['api_used']}/{quota['api_limit']} API calls, {quota['token_used']}/{quota['token_limit']} tokens"
    }

@router.get("/api/tenants")
def list_tenants(db: Session = Depends(get_db)):
    """List all tenants (admin view)"""
    tenants = db.query(Tenant).all()
    return [{"id": t.id, "name": t.name, "email": t.email, "plan_id": t.plan_id, "is_active": t.is_active} for t in tenants]

@router.get("/api/plans")
def list_plans(db: Session = Depends(get_db)):
    """List all plans"""
    from models.plan import Plan
    plans = db.query(Plan).all()
    return [{"id": p.id, "name": p.name, "api_limit": p.api_limit, "token_limit": p.token_limit} for p in plans]