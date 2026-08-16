class CostService:
    """Calculate costs based on pricing rules"""
    
    # Pricing constants (pinned)
    PRICE_PER_API_CALL = 0.001
    PRICE_PER_INPUT_TOKEN = 0.00001
    PRICE_PER_CACHED_INPUT_TOKEN = 0.000003  # 30% of input
    PRICE_PER_OUTPUT_TOKEN = 0.00002
    
    @staticmethod
    def calculate_cost(usage_type: str, quantity: float, plan_id: int = 1) -> float:
        """
        Calculate cost for a usage event.
        
        Pricing rules:
        - Cached input tokens are cheaper (30% of input)
        - Reasoning tokens count as output tokens
        """
        if plan_id == 1:  # Free plan - discounted rates
            multiplier = 1.0
        else:  # Pro plan
            multiplier = 0.8
        
        if usage_type == "api_call":
            return CostService.PRICE_PER_API_CALL * quantity * multiplier
        elif usage_type == "input_token":
            return CostService.PRICE_PER_INPUT_TOKEN * quantity * multiplier
        elif usage_type == "cached_input_token":
            return CostService.PRICE_PER_CACHED_INPUT_TOKEN * quantity * multiplier
        elif usage_type == "output_token":
            return CostService.PRICE_PER_OUTPUT_TOKEN * quantity * multiplier
        elif usage_type == "reasoning_token":
            # Reasoning tokens are priced as output tokens
            return CostService.PRICE_PER_OUTPUT_TOKEN * quantity * multiplier
        else:
            return 0.0
    
    @staticmethod
    def get_token_cost(input_tokens: float, cached_input_tokens: float, 
                       output_tokens: float, reasoning_tokens: float, 
                       plan_id: int = 1) -> dict:
        """
        Calculate total token cost with pricing rules.
        """
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