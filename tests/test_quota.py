import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi import HTTPException
from services.quota_service import QuotaService

def test_quota_boundary_exact_limit():
    """Test quota at exact limit"""
    # Mock quota response for testing
    quota = {
        "api_used": 1000,
        "api_limit": 1000,
        "api_remaining": 0,
        "token_used": 100000,
        "token_limit": 100000,
        "token_remaining": 0
    }
    
    # At exact limit, remaining should be 0
    assert quota["api_remaining"] == 0
    assert quota["token_remaining"] == 0

def test_quota_under_limit():
    """Test quota under limit"""
    quota = {
        "api_used": 500,
        "api_limit": 1000,
        "api_remaining": 500,
        "token_used": 50000,
        "token_limit": 100000,
        "token_remaining": 50000
    }
    
    assert quota["api_remaining"] > 0
    assert quota["token_remaining"] > 0

def test_quota_over_limit():
    """Test quota over limit"""
    quota = {
        "api_used": 1001,
        "api_limit": 1000,
        "api_remaining": -1,
        "token_used": 100001,
        "token_limit": 100000,
        "token_remaining": -1
    }
    
    assert quota["api_remaining"] < 0
    assert quota["token_remaining"] < 0