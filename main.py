from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from database import get_db

load_dotenv()

app = FastAPI(title="Usage Metering & Billing Engine", version="1.0")

# Import and include routes
from api.routes import router as api_router
app.include_router(api_router)

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