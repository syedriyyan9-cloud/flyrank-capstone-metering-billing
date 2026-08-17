import stripe
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from models import Tenant, Plan, Subscription
from datetime import datetime

load_dotenv()

# Debug: Print key (first few chars only)
key = os.getenv("STRIPE_SECRET_KEY")
print(f"Stripe key loaded: {key[:20] if key else 'NOT FOUND'}...")

# Initialize Stripe
stripe.api_key = key


class StripeService:
    
    @staticmethod
    def create_checkout_session(tenant_id: int, price_id: str, db: Session):
        """Create a Stripe Checkout session for a tenant"""
        
        # Validate Stripe API key is set
        if not stripe.api_key or not stripe.api_key.startswith("sk_test_"):
            return {
                "error": "Invalid Stripe API key. Please set STRIPE_SECRET_KEY in .env"
            }
        
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Get the plan
        plan = db.query(Plan).filter(Plan.stripe_price_id == price_id).first()
        if not plan:
            raise ValueError(f"Plan with price_id {price_id} not found")
        
        try:
            # Create or get Stripe customer
            if not tenant.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=tenant.email,
                    name=tenant.name,
                    metadata={"tenant_id": str(tenant_id)}
                )
                tenant.stripe_customer_id = customer.id
                db.commit()
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=tenant.stripe_customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                mode="subscription",
                success_url="http://localhost:8000/api/stripe/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="http://localhost:8000/api/stripe/cancel",
                metadata={
                    "tenant_id": str(tenant_id),
                    "plan_id": str(plan.id)
                }
            )
            
            return {
                "checkout_url": session.url,
                "session_id": session.id,
                "tenant_id": tenant_id,
                "plan_name": plan.name
            }
        except stripe.error.AuthenticationError:
            return {"error": "Invalid Stripe API key. Please check STRIPE_SECRET_KEY in .env"}
        except Exception as e:
            raise ValueError(f"Checkout creation failed: {str(e)}")
    
    @staticmethod
    def verify_webhook_signature(payload: bytes, signature: str) -> dict:
        """Verify Stripe webhook signature"""
        try:
            webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
            return {"valid": True, "event": event}
        except stripe.error.SignatureVerificationError as e:
            return {"valid": False, "error": str(e)}
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    @staticmethod
    def handle_checkout_completed(event: dict, db: Session):
        """Handle checkout.session.completed webhook"""
        session = event.data.object
        customer_id = session.customer
        subscription_id = session.subscription
        metadata = session.metadata
        
        tenant_id = int(metadata.get("tenant_id"))
        plan_id = int(metadata.get("plan_id"))
        
        # Get tenant
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Update tenant
        tenant.plan_id = plan_id
        tenant.stripe_customer_id = customer_id
        tenant.stripe_subscription_id = subscription_id
        tenant.is_active = True
        
        # Create subscription record
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if not subscription:
            subscription = Subscription(
                tenant_id=tenant_id,
                stripe_subscription_id=subscription_id,
                stripe_price_id=session.line_items.data[0].price.id if hasattr(session, 'line_items') else None,
                plan_id=plan_id,
                status="active",
                current_period_start=datetime.fromtimestamp(session.created),
                current_period_end=datetime.fromtimestamp(session.expires_at) if hasattr(session, 'expires_at') else None
            )
            db.add(subscription)
        
        db.commit()
        
        return {
            "tenant_id": tenant_id,
            "plan_id": plan_id,
            "customer_id": customer_id,
            "subscription_id": subscription_id,
            "status": "updated"
        }
    
    @staticmethod
    def handle_subscription_updated(event: dict, db: Session):
        """Handle customer.subscription.updated webhook"""
        subscription_data = event.data.object
        subscription_id = subscription_data.id
        
        # Find subscription in our DB
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        # Update status
        subscription.status = subscription_data.status
        subscription.current_period_start = datetime.fromtimestamp(subscription_data.current_period_start)
        subscription.current_period_end = datetime.fromtimestamp(subscription_data.current_period_end)
        
        # If subscription is cancelled, update tenant
        if subscription_data.status in ["cancelled", "incomplete_expired"]:
            tenant = db.query(Tenant).filter(Tenant.id == subscription.tenant_id).first()
            if tenant:
                tenant.plan_id = 1  # Downgrade to Free
                tenant.is_active = False
        
        db.commit()
        
        return {
            "subscription_id": subscription_id,
            "status": subscription_data.status,
            "updated": True
        }
    
    @staticmethod
    def handle_subscription_deleted(event: dict, db: Session):
        """Handle customer.subscription.deleted webhook"""
        subscription_data = event.data.object
        subscription_id = subscription_data.id
        
        # Find subscription
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        # Update tenant
        tenant = db.query(Tenant).filter(Tenant.id == subscription.tenant_id).first()
        if tenant:
            tenant.plan_id = 1  # Downgrade to Free
            tenant.is_active = False
            tenant.stripe_subscription_id = None
        
        # Update subscription status
        subscription.status = "deleted"
        
        db.commit()
        
        return {
            "subscription_id": subscription_id,
            "status": "deleted",
            "updated": True
        }