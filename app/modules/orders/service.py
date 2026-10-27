from sqlalchemy.orm import Session
from . import repository, models
from .exceptions import OrderNotFoundError, OrderOwnershipError


class InvalidOrderTransition(Exception):
    """Raised when a requested status transition is not allowed."""
    pass


class OrderStateMachine:
    """Finite state machine for order status transitions."""

    TRANSITIONS = {
        models.OrderStatus.RECEIVED: [
            models.OrderStatus.PROCESSING,
            models.OrderStatus.CANCELLED,
        ],
        models.OrderStatus.PROCESSING: [
            models.OrderStatus.FULFILLED,
            models.OrderStatus.CANCELLED,
        ],
        models.OrderStatus.FULFILLED: [
            models.OrderStatus.SHIPPED,
            models.OrderStatus.CANCELLED,
        ],
        models.OrderStatus.SHIPPED: [
            models.OrderStatus.DELIVERED
        ],
        models.OrderStatus.DELIVERED: [models.OrderStatus.RETURNED],
        models.OrderStatus.RETURNED: [],
        models.OrderStatus.CANCELLED: [],
    }

    @classmethod
    def validate_transition(cls, current: models.OrderStatus, target: models.OrderStatus) -> None:
        allowed = cls.TRANSITIONS.get(current)
        if allowed is None:
            raise InvalidOrderTransition(f"Unknown status: {current}")
        if target not in allowed:
            raise InvalidOrderTransition(
                f"Cannot transition from {current} to {target}"
            )


def create_order(repo: repository.OrderRepository, user_id: int, item: str):
    return repo.create_order(user_id, item)


def get_order(repo: repository.OrderRepository, order_id: int):
    order = repo.get_order(order_id)
    if not order:
        raise OrderNotFoundError()
    return order


def list_orders(repo: repository.OrderRepository, user_id: int | None = None, status: str | None = None, search: str | None = None, page: int = 1, page_size: int = 20):
    items, total = repo.list_orders(user_id=user_id, status=status, search=search, page=page, page_size=page_size)
    return items, total


def update_order(db: Session, repo: repository.OrderRepository, order_id: int, **kwargs):
    """Update an order with the provided fields. Raises OrderNotFoundError if not found."""
    order = repo.get_order(order_id)
    if not order:
        raise OrderNotFoundError()

    if "status" in kwargs and kwargs["status"] is not None:
        OrderStateMachine.validate_transition(order.status, kwargs["status"])

    for key, value in kwargs.items():
        if value is not None:
            setattr(order, key, value)
    try:
        db.commit()
        db.refresh(order)
    except Exception:
        db.rollback()
        raise
    return order


def delete_order(db: Session, repo: repository.OrderRepository, order_id: int):
    """Delete an order. Raises OrderNotFoundError if not found."""
    order = repo.get_order(order_id)
    if not order:
        raise OrderNotFoundError()
    try:
        repo.delete_order(order_id)
        db.commit()
    except Exception:
        db.rollback()
        raise


def cancel_order(db: Session, repo: repository.OrderRepository, order_id: int):
    """Cancel an order. Raises OrderNotFoundError if not found or OrderOwnershipError if already terminal."""
    order = repo.get_order(order_id)
    if not order:
        raise OrderNotFoundError()

    if order.status == models.OrderStatus.CANCELLED:
        raise OrderOwnershipError("Order is already cancelled")

    if order.status == models.OrderStatus.DELIVERED:
        raise OrderOwnershipError("Cannot cancel a delivered order")
    if order.status == models.OrderStatus.RETURNED:
        raise OrderOwnershipError("Cannot cancel a returned order")

    order.status = models.OrderStatus.CANCELLED
    try:
        db.commit()
        db.refresh(order)
    except Exception:
        db.rollback()
        raise
    return order


def require_order_ownership(repo: repository.OrderRepository, order_id: int, user_id: int):
    """Fetch an order and verify the user owns it. Raises OrderOwnershipError if not."""
    order = get_order(repo, order_id)
    if order.user_id != user_id:
        raise OrderOwnershipError()
    return order


def cancel_order_with_invoice(db: Session, order_repo: repository.OrderRepository, payment_repo, order_id: int):
    """Cancel an order and its associated invoice. Handles cross-module coupling."""
    from . import service as order_svc
    from app.modules.payment import service as payment_svc
    from app.modules.payment.service import PaymentError

    order = cancel_order(db, order_repo, order_id)
    try:
        payment_svc.cancel_invoice_by_order_id(payment_repo, order_id)
    except PaymentError as e:
        raise OrderOwnershipError(str(e))
    return order
