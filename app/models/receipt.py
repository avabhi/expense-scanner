import uuid
from sqlalchemy import Column, String, Float, Date, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base
from app.models.user import User

class Receipt(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=True, index=True)
    merchant_name = Column(String, nullable=True)
    date = Column(Date, nullable=True)
    total_amount = Column(Float, nullable=True)
    currency = Column(String(3), nullable=True)
    file_hash = Column(String, index=True, nullable=False)
    s3_object_key = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, processing, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="receipts")
    line_items = relationship("LineItem", back_populates="receipt", cascade="all, delete-orphan")

class LineItem(Base):
    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(UUID(as_uuid=True), ForeignKey("receipt.id", ondelete="CASCADE"), nullable=False)
    description = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    category = Column(String, nullable=True)  # AI-assigned spending category

    receipt = relationship("Receipt", back_populates="line_items")
