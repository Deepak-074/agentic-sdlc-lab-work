from datetime import datetime
from pydantic import BaseModel, ConfigDict
from .models import OrderStatus


class OrderCreate(BaseModel):
    item: str


class OrderUpdate(BaseModel):
    """Partial update schema for orders. Only provided fields are applied."""
    item: str | None = None
    status: OrderStatus | None = None


class OrderRead(BaseModel):
    id: int
    user_id: int
    item: str
    status: OrderStatus

    model_config = ConfigDict(from_attributes=True)


class PaginatedOrders(BaseModel):
    items: list[OrderRead]
    total: int
    page: int
    page_size: int


class OrderHistoryRead(BaseModel):
    id: int
    order_id: int
    status: OrderStatus
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)
