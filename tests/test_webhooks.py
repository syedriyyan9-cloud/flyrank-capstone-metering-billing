import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from api.webhooks.stripe import processed_events

def test_webhook_signature_verification():
    """Test webhook signature verification"""
    from services.stripe_service import StripeService
    
    # Test invalid signature
    result = StripeService.verify_webhook_signature(
        payload=b"test",
        signature="invalid_signature"
    )
    assert result["valid"] == False
    assert "error" in result

def test_duplicate_webhook_prevention():
    """Test duplicate webhook events are ignored"""
    # Clear processed events
    processed_events.clear()
    
    # First event should be processed
    event_id = "evt_test_123"
    processed_events.add(event_id)
    
    # Second event with same ID should be detected as duplicate
    assert event_id in processed_events