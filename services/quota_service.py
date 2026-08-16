from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Tenant, Plan, UsageEvent
from datetime import datetime
from fastapi import HTTPException, status

class QuotaService:
    
    @staticmethod
    def check_quota(tenant_id: int, db: Session):
        """Check if tenant has remaining quota for the current month"""
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        plan = db.query(Plan).filter(Plan.id == tenant.plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Calculate current month usage
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # API call usage
        api_used = db.query(func.sum(UsageEvent.quantity)).filter(
            UsageEvent.tenant_id == tenant_id,
            UsageEvent.usage_type == "api_call",
            UsageEvent.timestamp >= start_of_month
        ).scalar() or 0
        
        # Token usage
        token_used = db.query(func.sum(UsageEvent.quantity)).filter(
            UsageEvent.tenant_id == tenant_id,
            UsageEvent.usage_type.in_(["input_token", "cached_input_token", "output_token", "reasoning_token"]),
            UsageEvent.timestamp >= start_of_month
        ).scalar() or 0
        
        api_remaining = plan.api_limit - api_used
        token_remaining = plan.token_limit - token_used
        
        return {
            "tenant_id": tenant_id,
            "plan_name": plan.name,
            "api_used": round(float(api_used), 2),
            "api_limit": plan.api_limit,
            "api_remaining": round(float(api_remaining), 2),
            "token_used": round(float(token_used), 2),
            "token_limit": plan.token_limit,
            "token_remaining": round(float(token_remaining), 2),
            "has_api_quota": api_remaining > 0,
            "has_token_quota": token_remaining > 0
        }
    
    @staticmethod
    def enforce_quota(tenant_id: int, usage_type: str, quantity: float, db: Session):
        """Enforce quota before allowing usage"""
        quota = QuotaService.check_quota(tenant_id, db)
        
        if usage_type == "api_call":
            if quota["api_remaining"] < quantity:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"API quota exceeded. Used {quota['api_used']}/{quota['api_limit']}. Upgrade to Pro for higher limits."
                )
        elif usage_type in ["input_token", "cached_input_token", "output_token", "reasoning_token", "token_bundle"]:
            if quota["token_remaining"] < quantity:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Token quota exceeded. Used {quota['token_used']}/{quota['token_limit']}. Upgrade to Pro for higher limits."
                )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown usage type: {usage_type}")
        
        return quota