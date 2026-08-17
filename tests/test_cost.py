import pytest
from services.cost_service import CostService

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_pricing_constants_are_pinned():
    """Test pricing constants are pinned and don't change"""
    assert CostService.PRICE_PER_API_CALL == 0.001
    assert CostService.PRICE_PER_INPUT_TOKEN == 0.00001
    assert CostService.PRICE_PER_CACHED_INPUT_TOKEN == 0.000003
    assert CostService.PRICE_PER_OUTPUT_TOKEN == 0.00002
    assert CostService.PRICE_PER_REASONING_TOKEN == 0.00002

def test_cached_input_tokens_are_cheaper():
    """Test cached input tokens are 30% of input tokens"""
    input_cost = CostService.calculate_cost("input_token", 100, plan_id=1)
    cached_cost = CostService.calculate_cost("cached_input_token", 100, plan_id=1)
    # Use pytest.approx for floating-point comparison
    assert cached_cost == pytest.approx(input_cost * 0.3)

def test_reasoning_tokens_equal_output_tokens():
    """Test reasoning tokens are priced the same as output tokens"""
    output_cost = CostService.calculate_cost("output_token", 100, plan_id=1)
    reasoning_cost = CostService.calculate_cost("reasoning_token", 100, plan_id=1)
    assert output_cost == reasoning_cost

def test_pro_plan_gets_20_percent_discount():
    """Test Pro plan gets 20% discount on all prices"""
    free_cost = CostService.calculate_cost("api_call", 100, plan_id=1)
    pro_cost = CostService.calculate_cost("api_call", 100, plan_id=2)
    assert pro_cost == free_cost * 0.8

def test_token_bundle_cost_calculation():
    """Test token bundle cost calculation with all token types"""
    result = CostService.get_token_cost(
        input_tokens=1000,
        cached_input_tokens=500,
        output_tokens=200,
        reasoning_tokens=50,
        plan_id=1
    )
    
    # Verify all components are present
    assert "input_cost" in result
    assert "cached_input_cost" in result
    assert "output_cost" in result
    assert "reasoning_cost" in result
    assert "total_cost" in result
    
    # Total should equal sum of parts
    expected_total = (result["input_cost"] + result["cached_input_cost"] +
                      result["output_cost"] + result["reasoning_cost"])
    assert result["total_cost"] == expected_total

def test_zero_tokens_cost_zero():
    """Test zero tokens cost zero"""
    result = CostService.get_token_cost(0, 0, 0, 0, plan_id=1)
    assert result["total_cost"] == 0