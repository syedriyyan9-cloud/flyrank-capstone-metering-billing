from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from services.stripe_service import StripeService
from typing import Optional
import os

from database import get_db  # Import from database.py instead of main.py

router = APIRouter(prefix="/api/webhooks/stripe", tags=["Webhooks"])

# Store processed event IDs to prevent duplicates
processed_events = set()

@router.post("")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events"""
    try:
        # Get raw body
        body = await request.body()
        signature = request.headers.get("stripe-signature")
        
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe-signature header"
            )
        
        # Verify signature
        verification = StripeService.verify_webhook_signature(body, signature)
        
        if not verification["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid webhook signature: {verification.get('error')}"
            )
        
        event = verification["event"]
        event_id = event.id
        event_type = event.type
        
        # Check for duplicate event
        if event_id in processed_events:
            return {
                "status": "ignored",
                "message": "Duplicate webhook event",
                "event_id": event_id
            }
        
        try:
            result = None
            
            if event_type == "checkout.session.completed":
                result = StripeService.handle_checkout_completed(event, db)
            elif event_type == "customer.subscription.updated":
                result = StripeService.handle_subscription_updated(event, db)
            elif event_type == "customer.subscription.deleted":
                result = StripeService.handle_subscription_deleted(event, db)
            else:
                return {
                    "status": "ignored",
                    "message": f"Unhandled event type: {event_type}",
                    "event_id": event_id
                }
            
            processed_events.add(event_id)
            
            return {
                "status": "processed",
                "event_id": event_id,
                "event_type": event_type,
                "result": result
            }
            
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Webhook processing failed: {str(e)}"
            )
            
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )

@router.get("/check")
async def webhook_check():
    """Health check for webhook endpoint"""
    return {
        "status": "ok",
        "webhook_url": "/api/webhooks/stripe",
        "processed_events_count": len(processed_events),
        "processed_events": list(processed_events)[-10:]
    }