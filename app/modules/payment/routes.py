from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import service, schemas
from .models import InvoiceStatus
from app.core.auth import get_current_user
from app.core import dependencies as deps
from app.db.session import get_db
from app.modules.orders.exceptions import OrderNotFoundError
from .service import PaymentError, InvoiceNotFoundError
from app.modules.orders.service import InvalidOrderTransition

router = APIRouter()


@router.post("/generate", response_model=schemas.InvoiceRead)
def generate_invoice(
    payload: schemas.InvoiceCreate,
    db: Session = Depends(get_db),
    invoice_repo: deps.InvoiceRepository = Depends(deps.get_payment_repository),
    order_repo: deps.OrderRepository = Depends(deps.get_orders_repository),
    _user: str = Depends(get_current_user),
):
    try:
        return service.generate_invoice(db, order_repo, invoice_repo, payload.order_id)
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except PaymentError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pay/{order_id}", response_model=schemas.InvoiceRead)
def pay_invoice(
    order_id: int,
    db: Session = Depends(get_db),
    invoice_repo: deps.InvoiceRepository = Depends(deps.get_payment_repository),
    order_repo: deps.OrderRepository = Depends(deps.get_orders_repository),
    _user: str = Depends(get_current_user),
):
    try:
        return service.mark_invoice_paid_by_order_id(db, invoice_repo, order_repo, order_id)
    except InvoiceNotFoundError:
        raise HTTPException(status_code=404, detail="Invoice not found")
    except PaymentError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoice/{invoice_id}", response_model=schemas.InvoiceRead)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    invoice_repo: deps.InvoiceRepository = Depends(deps.get_payment_repository),
    _user: str = Depends(get_current_user),
):
    try:
        return service.get_invoice(invoice_repo, invoice_id)
    except InvoiceNotFoundError:
        raise HTTPException(status_code=404, detail="Invoice not found")


@router.get("/invoice/order/{order_id}", response_model=schemas.InvoiceRead)
def get_invoice_by_order(
    order_id: int,
    db: Session = Depends(get_db),
    invoice_repo: deps.InvoiceRepository = Depends(deps.get_payment_repository),
    _user: str = Depends(get_current_user),
):
    try:
        return service.get_invoice_by_order(invoice_repo, order_id)
    except InvoiceNotFoundError:
        raise HTTPException(status_code=404, detail="Invoice not found")


@router.get("/", response_model=schemas.PaginatedInvoices)
def list_invoices(
    page: int = 1,
    page_size: int = 20,
    status: InvoiceStatus | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    invoice_repo: deps.InvoiceRepository = Depends(deps.get_payment_repository),
    _user: str = Depends(get_current_user),
):
    items, total = service.list_invoices(invoice_repo, status=status, search=search, page=page, page_size=page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/refund/{order_id}", response_model=schemas.InvoiceRead)
def refund_invoice(
    order_id: int,
    db: Session = Depends(get_db),
    invoice_repo: deps.InvoiceRepository = Depends(deps.get_payment_repository),
    order_repo: deps.OrderRepository = Depends(deps.get_orders_repository),
    _user: str = Depends(get_current_user),
):
    try:
        return service.refund_invoice(db, invoice_repo, order_repo, order_id)
    except (InvoiceNotFoundError, OrderNotFoundError):
        raise HTTPException(status_code=404, detail="Invoice not found")
    except (PaymentError, InvalidOrderTransition) as e:
        raise HTTPException(status_code=400, detail=str(e))
