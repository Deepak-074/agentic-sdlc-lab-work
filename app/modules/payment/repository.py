from sqlalchemy.orm import Session
from . import models


class InvoiceRepository:
    def __init__(self, db: Session):
        self._db = db

    def create_invoice(self, order_id: int, external_invoice_id: str | None = None):
        invoice = models.Invoice(
            order_id=order_id,
            external_invoice_id=external_invoice_id,
        )
        self._db.add(invoice)
        self._db.commit()
        self._db.refresh(invoice)
        return invoice

    def get_invoice(self, invoice_id: int):
        return self._db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()

    def get_invoice_by_order_id(self, order_id: int):
        return self._db.query(models.Invoice).filter(models.Invoice.order_id == order_id).first()

    def get_invoice_by_external_id(self, external_invoice_id: str):
        return self._db.query(models.Invoice).filter(
            models.Invoice.external_invoice_id == external_invoice_id
        ).first()

    def list_invoices(self, status: str | None = None, search: str | None = None, page: int = 1, page_size: int = 20):
        query = self._db.query(models.Invoice)
        if status is not None:
            query = query.filter(models.Invoice.status == status)
        if search is not None:
            query = query.filter(models.Invoice.external_invoice_id.ilike(f"%{search}%"))
        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(models.Invoice.id).offset(offset).limit(page_size).all()
        return items, total

    def update_invoice(self, invoice_id: int, **kwargs):
        invoice = self._db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("Invoice not found")
        for field, value in kwargs.items():
            if value is not None:
                setattr(invoice, field, value)
        return invoice

    def update_invoice_by_order_id(self, order_id: int, **kwargs):
        invoice = self._db.query(models.Invoice).filter(models.Invoice.order_id == order_id).first()
        if not invoice:
            raise ValueError("Invoice not found")
        for field, value in kwargs.items():
            if value is not None:
                setattr(invoice, field, value)
        return invoice

    def settle_invoice_and_advance_order(self, invoice_id: int, order_id: int, order_status):
        """Atomically mark invoice as PAID and update order status in a single transaction."""
        from app.modules.orders import models as order_models
        invoice = self._db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("Invoice not found")
        invoice.status = models.InvoiceStatus.PAID

        order = self._db.query(order_models.Order).filter(order_models.Order.id == order_id).first()
        if not order:
            self._db.rollback()
            raise ValueError("Order not found")
        order.status = order_status
        from app.modules.orders.repository import OrderRepository
        OrderRepository(self._db).add_history(order_id, order_status)

        self._db.commit()
        self._db.refresh(invoice)
        self._db.refresh(order)
        return invoice, order
