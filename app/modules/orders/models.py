from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime
from sqlalchemy.sql import func
from app.db.session import Base
import enum


class OrderStatus(str, enum.Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    FULFILLED = "fulfilled"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    item = Column(String, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.RECEIVED)


class OrderStatusHistory(Base):
    """Append-only record of every status an order has had."""
    __tablename__ = "order_status_history"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    status = Column(Enum(OrderStatus), nullable=False)
    changed_at = Column(DateTime, default=func.now(), nullable=False)
