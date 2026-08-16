import pytest
from services.cost_service import CostService

def test_cost_calculation_basic():
    """Test basic cost calculation"""
    cost = CostService.calculate_cost("api_call", 1, plan_id=1)
    assert cost == 0.001
    
    cost = CostService.calculate_cost("input_token", 100, plan_id=1)
    assert cost == 0.001  # 100 * 0.00001 = 0.001

def test_cached_input_tokens_are_cheaper():
    """Test cached input tokens are priced at 30% of input"""
    input_cost = CostService.calculate_cost("input_token", 100, plan_id=1)
    cached_cost = CostService.calculate_cost("cached_input_token", 100, plan_id=1)
    assert cached_cost < input_cost
    assert cached_cost == input_cost * 0.3

def test_reasoning_tokens_count_as_output():
    """Test reasoning tokens are priced as output tokens"""
    output_cost = CostService.calculate_cost("output_token", 100, plan_id=1)
    reasoning_cost = CostService.calculate_cost("reasoning_token", 100, plan_id=1)
    assert output_cost == reasoning_cost

def test_token_bundle_cost():
    """Test token bundle cost calculation"""
    result = CostService.get_token_cost(
        input_tokens=100,
        cached_input_tokens=50,
        output_tokens=75,
        reasoning_tokens=25,
        plan_id=1
    )
    
    # Verify each component
    assert result["input_cost"] > 0
    assert result["cached_input_cost"] > 0
    assert result["output_cost"] > 0
    assert result["reasoning_cost"] == result["output_cost"] * 0.25  # 25 vs 75 = 1/3
    assert result["total_cost"] > 0

def test_pro_plan_discount():
    """Test Pro plan gets 20% discount"""
    free_cost = CostService.calculate_cost("api_call", 100, plan_id=1)
    pro_cost = CostService.calculate_cost("api_call", 100, plan_id=2)
    assert pro_cost < free_cost
    assert pro_cost == free_cost * 0.8