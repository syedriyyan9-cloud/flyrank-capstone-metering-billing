from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

app = FastAPI(title="Usage Metering & Billing Engine", version="1.0")

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL not set in .env file")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Import and include routes
from api.routes import router
app.include_router(router)

# Import and include webhook routes
from api.webhooks.stripe import router as webhook_router
app.include_router(webhook_router)

@app.get("/")
def root():
    return {"message": "Usage Metering & Billing Engine", "version": "1.0"}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")

@app.get("/version")
def version():
    return {"version": "1.0.0", "name": "Usage Metering & Billing Engine"}