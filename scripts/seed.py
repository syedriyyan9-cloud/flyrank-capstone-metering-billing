import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Plan, Tenant
from dotenv import load_dotenv

# Load .env from parent directory
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found in .env file")
    print("   Please create .env file with DATABASE_URL=postgresql://...")
    sys.exit(1)

print(f"✅ Using DATABASE_URL: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_plans(db):
    plans = [
        Plan(
            id=1,
            name="Free",
            api_limit=1000,
            token_limit=100000,
            price_per_api_call=0.001,
            price_per_input_token=0.00001,
            price_per_cached_input_token=0.000003,
            price_per_output_token=0.00002,
            stripe_price_id="price_free"
        ),
        Plan(
            id=2,
            name="Pro",
            api_limit=10000,
            token_limit=1000000,
            price_per_api_call=0.0008,
            price_per_input_token=0.000008,
            price_per_cached_input_token=0.0000024,
            price_per_output_token=0.000016,
            stripe_price_id="price_pro"
        )
    ]
    
    for plan in plans:
        existing = db.query(Plan).filter(Plan.id == plan.id).first()
        if not existing:
            db.add(plan)
    
    db.commit()
    print("✅ Plans seeded successfully")

def seed_demo_tenant(db):
    tenant = db.query(Tenant).filter(Tenant.email == "demo@example.com").first()
    if not tenant:
        tenant = Tenant(
            name="Demo Tenant",
            email="demo@example.com",
            plan_id=1,
            is_active=True
        )
        db.add(tenant)
        db.commit()
        print(f"✅ Demo tenant created with ID: {tenant.id}")
    else:
        print(f"ℹ️ Demo tenant already exists with ID: {tenant.id}")
    return tenant.id

def main():
    try:
        db = SessionLocal()
        
        # Create tables
        Base.metadata.create_all(engine)
        print("✅ Database tables created")
        
        # Seed plans
        seed_plans(db)
        
        # Seed demo tenant
        tenant_id = seed_demo_tenant(db)
        
        print("\n✅ Database seeding complete!")
        print(f"   Tenant ID: {tenant_id}")
        print("   Plan: Free (ID: 1)")
        
        db.close()
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()