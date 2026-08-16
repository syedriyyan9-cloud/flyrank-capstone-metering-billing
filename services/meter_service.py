from sqlalchemy.orm import Session
from models import UsageEvent, Tenant
from services.cost_service import CostService
from services.quota_service import QuotaService
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

class MeterService:
    
    @staticmethod
    def record_usage(tenant_id: int, idempotency_key: str, usage_type: str, 
                     quantity: float, db: Session) -> dict:
        """
        Record a usage event with idempotency.
        
        Returns:
            - If duplicate key: returns the existing event
            - If new: records and returns the new event
        """
        # Check if idempotency key already exists (duplicate prevention)
        existing = db.query(UsageEvent).filter(
            UsageEvent.idempotency_key == idempotency_key
        ).first()
        
        if existing:
            return {
                "id": existing.id,
                "tenant_id": existing.tenant_id,
                "usage_type": existing.usage_type,
                "quantity": existing.quantity,
                "cost": existing.cost,
                "timestamp": existing.timestamp.isoformat(),
                "duplicate": True,
                "message": "Duplicate request - using cached result"
            }
        
        # Enforce quota
        QuotaService.enforce_quota(tenant_id, usage_type, quantity, db)
        
        # Calculate cost
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        cost = CostService.calculate_cost(usage_type, quantity, tenant.plan_id)
        
        # Record usage event
        usage_event = UsageEvent(
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            usage_type=usage_type,
            quantity=quantity,
            cost=cost
        )
        
        try:
            db.add(usage_event)
            db.commit()
            db.refresh(usage_event)
        except IntegrityError:
            db.rollback()
            # Check if it was a race condition duplicate
            existing = db.query(UsageEvent).filter(
                UsageEvent.idempotency_key == idempotency_key
            ).first()
            if existing:
                return {
                    "id": existing.id,
                    "tenant_id": existing.tenant_id,
                    "usage_type": existing.usage_type,
                    "quantity": existing.quantity,
                    "cost": existing.cost,
                    "timestamp": existing.timestamp.isoformat(),
                    "duplicate": True,
                    "message": "Duplicate request (race condition) - using cached result"
                }
            raise
        
        return {
            "id": usage_event.id,
            "tenant_id": usage_event.tenant_id,
            "usage_type": usage_event.usage_type,
            "quantity": usage_event.quantity,
            "cost": usage_event.cost,
            "timestamp": usage_event.timestamp.isoformat(),
            "duplicate": False,
            "message": "Usage recorded successfully"
        }
    
    @staticmethod
    def get_usage_summary(tenant_id: int, db: Session) -> dict:
        """Get monthly usage summary"""
        from sqlalchemy import func
        from datetime import datetime
        
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get all usage for the month
        events = db.query(UsageEvent).filter(
            UsageEvent.tenant_id == tenant_id,
            UsageEvent.timestamp >= start_of_month
        ).all()
        
        total_api_calls = sum(e.quantity for e in events if e.usage_type == "api_call")
        total_tokens = sum(e.quantity for e in events if e.usage_type in ["input_token", "cached_input_token", "output_token", "reasoning_token"])
        total_cost = sum(e.cost for e in events)
        
        # Get plan info
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        from models.plan import Plan
        plan = db.query(Plan).filter(Plan.id == tenant.plan_id).first()
        
        return {
            "tenant_id": tenant_id,
            "plan_name": plan.name,
            "usage": {
                "api_calls": {
                    "used": round(total_api_calls, 2),
                    "limit": plan.api_limit,
                    "remaining": round(plan.api_limit - total_api_calls, 2)
                },
                "tokens": {
                    "used": round(total_tokens, 2),
                    "limit": plan.token_limit,
                    "remaining": round(plan.token_limit - total_tokens, 2)
                },
                "total_cost": round(total_cost, 6)
            }
        }