from sqlalchemy import Column, Integer, String, ForeignKey, Enum
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
