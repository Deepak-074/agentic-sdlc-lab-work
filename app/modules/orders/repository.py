from sqlalchemy.orm import Session
from . import models


class OrderRepository:
    def __init__(self, db: Session):
        self._db = db

    def create_order(self, user_id: int, item: str):
        order = models.Order(user_id=user_id, item=item)
        self._db.add(order)
        self._db.flush()
        self.add_history(order.id, models.OrderStatus.RECEIVED)
        self._db.commit()
        self._db.refresh(order)
        return order

    def get_order(self, order_id: int):
        return self._db.query(models.Order).filter(models.Order.id == order_id).first()

    def list_orders(self, user_id: int | None = None, status: str | None = None, search: str | None = None, page: int = 1, page_size: int = 20):
        query = self._db.query(models.Order)
        if user_id is not None:
            query = query.filter(models.Order.user_id == user_id)
        if status is not None:
            query = query.filter(models.Order.status == status)
        if search is not None:
            query = query.filter(models.Order.item.ilike(f"%{search}%"))
        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(models.Order.id).offset(offset).limit(page_size).all()
        return items, total

    def update_order(self, order_id: int, **kwargs):
        order = self._db.query(models.Order).filter(models.Order.id == order_id).first()
        if not order:
            raise ValueError("Order not found")
        for field, value in kwargs.items():
            if value is not None:
                setattr(order, field, value)
        return order

    def delete_order(self, order_id: int):
        order = self._db.query(models.Order).filter(models.Order.id == order_id).first()
        if not order:
            raise ValueError("Order not found")
        self._db.delete(order)
        return True

    def save(self, order):
        self._db.add(order)
        self._db.commit()
        self._db.refresh(order)
        return order

    def add_history(self, order_id: int, status) -> None:
        """Queue a history row. The caller commits, so the row is atomic with the status change."""
        self._db.add(models.OrderStatusHistory(order_id=order_id, status=status))

    def list_history(self, order_id: int):
        return (
            self._db.query(models.OrderStatusHistory)
            .filter(models.OrderStatusHistory.order_id == order_id)
            .order_by(models.OrderStatusHistory.id)
            .all()
        )
