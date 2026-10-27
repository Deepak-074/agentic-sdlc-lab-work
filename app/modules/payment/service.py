import uuid
from sqlalchemy.orm import Session
from . import repository, models as payment_models
from app.modules.orders import service as order_service
from app.modules.orders import repository as order_repo
from app.modules.orders import models as order_models
from app.modules.orders.exceptions import OrderNotFoundError
from app.modules.orders.service import OrderStateMachine


class PaymentError(Exception):
    """Raised when a payment operation fails."""
    pass


class InvoiceNotFoundError(Exception):
    """Raised when an invoice is not found."""
    pass


def generate_invoice(db: Session, order_repo: order_repo.OrderRepository, invoice_repo: repository.InvoiceRepository, order_id: int):
    """
    Generate an invoice for an order.
    - Validates the order exists and is in RECEIVED status.
    - Calls the payment API to create an invoice (simulated with external_invoice_id).
    - Transitions order status from RECEIVED to PROCESSING.
    """
    order = order_repo.get_order(order_id)
    if not order:
        raise OrderNotFoundError()

    if order.status != order_models.OrderStatus.RECEIVED:
        raise PaymentError(
            f"Cannot generate invoice for order in '{order.status.value}' status. "
            "Order must be in 'received' status."
        )

    # Check if invoice already exists for this order
    existing_invoice = invoice_repo.get_invoice_by_order_id(order_id)
    if existing_invoice:
        raise PaymentError("Invoice already exists for this order")

    # Call payment API to generate invoice (simulated)
    external_invoice_id = _call_payment_api_create_invoice(order_id)

    # Create invoice record
    try:
        invoice = invoice_repo.create_invoice(order_id, external_invoice_id)
        order_service.update_order(db, order_repo, order_id, status=order_models.OrderStatus.PROCESSING)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return invoice


def _call_payment_api_create_invoice(order_id: int) -> str:
    """
    Simulate calling an external payment API to generate an invoice.
    In a real implementation, this would make an HTTP call to the payment provider.
    """
    external_id = f"inv-{uuid.uuid4().hex[:12]}"
    return external_id


def mark_invoice_paid(db: Session, invoice_repo: repository.InvoiceRepository, order_repo: order_repo.OrderRepository, invoice_id: int):
    """
    Handle invoice payment completion by invoice ID.
    - Finds the invoice by invoice_id.
    - Marks invoice as PAID.
    - Transitions order status from PROCESSING to FULFILLED.
    - All changes are committed in a single atomic transaction.
    """
    invoice = invoice_repo.get_invoice(invoice_id)
    if not invoice:
        raise InvoiceNotFoundError(f"Invoice {invoice_id} not found")

    if invoice.status == payment_models.InvoiceStatus.PAID:
        raise PaymentError("Invoice is already marked as paid")

    invoice, order = invoice_repo.settle_invoice_and_advance_order(
        invoice_id, invoice.order_id, order_models.OrderStatus.FULFILLED
    )
    return invoice


def mark_invoice_paid_by_order_id(db: Session, invoice_repo: repository.InvoiceRepository, order_repo: order_repo.OrderRepository, order_id: int):
    """
    Handle invoice payment completion via order_id.
    - Finds the invoice by order_id.
    - Marks invoice as PAID.
    - Transitions order status from PROCESSING to FULFILLED.
    - All changes are committed in a single atomic transaction.
    """
    invoice = invoice_repo.get_invoice_by_order_id(order_id)
    if not invoice:
        raise InvoiceNotFoundError(f"No invoice found for order {order_id}")

    if invoice.status == payment_models.InvoiceStatus.PAID:
        raise PaymentError("Invoice is already marked as paid")

    invoice, order = invoice_repo.settle_invoice_and_advance_order(
        invoice.id, order_id, order_models.OrderStatus.FULFILLED
    )
    return invoice


def get_invoice(invoice_repo: repository.InvoiceRepository, invoice_id: int):
    invoice = invoice_repo.get_invoice(invoice_id)
    if not invoice:
        raise InvoiceNotFoundError(f"Invoice {invoice_id} not found")
    return invoice


def get_invoice_by_order(invoice_repo: repository.InvoiceRepository, order_id: int):
    invoice = invoice_repo.get_invoice_by_order_id(order_id)
    if not invoice:
        raise InvoiceNotFoundError(f"No invoice found for order {order_id}")
    return invoice


def list_invoices(invoice_repo: repository.InvoiceRepository, status: str | None = None, search: str | None = None, page: int = 1, page_size: int = 20):
    items, total = invoice_repo.list_invoices(status=status, search=search, page=page, page_size=page_size)
    return items, total


def cancel_invoice_by_order_id(invoice_repo: repository.InvoiceRepository, order_id: int):
    """Cancel the invoice associated with an order. No-op if no invoice exists."""
    invoice = invoice_repo.get_invoice_by_order_id(order_id)
    if not invoice:
        return None
    if invoice.status == payment_models.InvoiceStatus.CANCELLED:
        return invoice
    if invoice.status == payment_models.InvoiceStatus.PAID:
        raise PaymentError("Cannot cancel a paid invoice")
    return invoice_repo.update_invoice(invoice.id, status=payment_models.InvoiceStatus.CANCELLED)


def refund_invoice(db: Session, invoice_repo: repository.InvoiceRepository, order_repo: order_repo.OrderRepository, order_id: int):
    """Refund a PAID invoice: the invoice becomes CANCELLED and the order becomes CANCELLED.

    The order transition is validated by the state machine, so a SHIPPED or DELIVERED order cannot be refunded.
    """
    invoice = invoice_repo.get_invoice_by_order_id(order_id)
    if not invoice:
        raise InvoiceNotFoundError(f"No invoice found for order {order_id}")
    if invoice.status != payment_models.InvoiceStatus.PAID:
        raise PaymentError("Only paid invoices can be refunded")
    order = order_repo.get_order(order_id)
    if not order:
        raise OrderNotFoundError()
    OrderStateMachine.validate_transition(order.status, order_models.OrderStatus.CANCELLED)
    try:
        invoice.status = payment_models.InvoiceStatus.CANCELLED
        order.status = order_models.OrderStatus.CANCELLED
        order_repo.add_history(order_id, order_models.OrderStatus.CANCELLED)
        db.commit()
        db.refresh(invoice)
    except Exception:
        db.rollback()
        raise
    return invoice
