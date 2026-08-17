class CostService:
    """Calculate costs based on pricing rules with pinned constants"""
    
    # Pricing constants (pinned - these are the source of truth)
    PRICE_PER_API_CALL = 0.001
    PRICE_PER_INPUT_TOKEN = 0.00001
    PRICE_PER_CACHED_INPUT_TOKEN = 0.000003  # 30% of input
    PRICE_PER_OUTPUT_TOKEN = 0.00002
    PRICE_PER_REASONING_TOKEN = 0.00002  # Same as output
    
    @staticmethod
    def calculate_cost(usage_type: str, quantity: float, plan_id: int = 1) -> float:
        """Calculate cost for a usage event with plan multiplier"""
        # Plan multiplier: Free = 1.0, Pro = 0.8 (20% discount)
        multiplier = 1.0 if plan_id == 1 else 0.8
        
        pricing = {
            "api_call": CostService.PRICE_PER_API_CALL,
            "input_token": CostService.PRICE_PER_INPUT_TOKEN,
            "cached_input_token": CostService.PRICE_PER_CACHED_INPUT_TOKEN,
            "output_token": CostService.PRICE_PER_OUTPUT_TOKEN,
            "reasoning_token": CostService.PRICE_PER_REASONING_TOKEN,
            "token_bundle": CostService.PRICE_PER_INPUT_TOKEN  # Fallback
        }
        
        price = pricing.get(usage_type, 0)
        return price * quantity * multiplier
    
    @staticmethod
    def get_token_cost(input_tokens: float, cached_input_tokens: float,
                       output_tokens: float, reasoning_tokens: float,
                       plan_id: int = 1) -> dict:
        """Calculate total token cost with pricing rules"""
        input_cost = CostService.calculate_cost("input_token", input_tokens, plan_id)
        cached_cost = CostService.calculate_cost("cached_input_token", cached_input_tokens, plan_id)
        output_cost = CostService.calculate_cost("output_token", output_tokens, plan_id)
        reasoning_cost = CostService.calculate_cost("reasoning_token", reasoning_tokens, plan_id)
        
        return {
            "input_cost": round(input_cost, 6),
            "cached_input_cost": round(cached_cost, 6),
            "output_cost": round(output_cost, 6),
            "reasoning_cost": round(reasoning_cost, 6),
            "total_cost": round(input_cost + cached_cost + output_cost + reasoning_cost, 6)
        }
    
    @staticmethod
    def get_monthly_usage_cost(tenant_id: int, db) -> dict:
        """Get cost rollup for a tenant's monthly usage"""
        from sqlalchemy import func
        from models import UsageEvent, Tenant, Plan
        from datetime import datetime
        
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get tenant and plan
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return {"error": "Tenant not found"}
        
        plan = db.query(Plan).filter(Plan.id == tenant.plan_id).first()
        
        # Get all usage for the month
        events = db.query(UsageEvent).filter(
            UsageEvent.tenant_id == tenant_id,
            UsageEvent.timestamp >= start_of_month
        ).all()
        
        # Calculate costs by type
        api_calls = sum(e.quantity for e in events if e.usage_type == "api_call")
        api_cost = sum(e.cost for e in events if e.usage_type == "api_call")
        
        token_events = [e for e in events if e.usage_type in ["input_token", "cached_input_token", "output_token", "reasoning_token", "token_bundle"]]
        total_tokens = sum(e.quantity for e in token_events)
        token_cost = sum(e.cost for e in token_events)
        
        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "plan_name": plan.name if plan else "Unknown",
            "period": f"{start_of_month.strftime('%Y-%m')}",
            "usage": {
                "api_calls": round(api_calls, 2),
                "tokens": round(total_tokens, 2)
            },
            "costs": {
                "api_cost": round(api_cost, 6),
                "token_cost": round(token_cost, 6),
                "total_cost": round(api_cost + token_cost, 6)
            }
        }