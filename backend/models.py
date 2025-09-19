from sqlalchemy import Column, Integer, String, TIMESTAMP, func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(150), unique=True, index=True, nullable=False)
    password = Column(String(200), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
