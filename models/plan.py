from sqlalchemy import Column, Integer, String, Float
from .base import Base

class Plan(Base):
    __tablename__ = "plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    api_limit = Column(Integer, nullable=False)
    token_limit = Column(Integer, nullable=False)
    price_per_api_call = Column(Float, nullable=False)
    price_per_input_token = Column(Float, nullable=False)
    price_per_cached_input_token = Column(Float, nullable=False)
    price_per_output_token = Column(Float, nullable=False)
    stripe_price_id = Column(String(255), nullable=True)