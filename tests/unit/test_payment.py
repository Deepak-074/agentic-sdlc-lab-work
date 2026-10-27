from unittest.mock import MagicMock, patch
import pytest

from app.modules.payment import service, repository, models as payment_models
from app.modules.orders import models as order_models
from app.modules.orders.repository import OrderRepository
from app.modules.payment.service import PaymentError, InvoiceNotFoundError


def _make_mock_invoice_repo(invoice=None):
    repo = MagicMock(spec=repository.InvoiceRepository)
    repo._db = MagicMock()
    repo.get_invoice.return_value = invoice
    repo.get_invoice_by_order_id.return_value = invoice
    repo.get_invoice_by_external_id.return_value = invoice
    repo.settle_invoice_and_advance_order.return_value = (invoice, MagicMock())
    return repo


def _make_mock_order_repo(order=None):
    repo = MagicMock(spec=OrderRepository)
    repo._db = MagicMock()
    repo.get_order.return_value = order
    return repo


def _make_db():
    db = MagicMock()
    return db


def _make_invoice(order_id=1, status="pending"):
    invoice = MagicMock(spec=payment_models.Invoice)
    invoice.id = 1
    invoice.order_id = order_id
    invoice.status = status
    invoice.external_invoice_id = "inv-test123"
    return invoice


def _make_order(item="widget", status="received"):
    order = MagicMock(spec=order_models.Order)
    order.id = 1
    order.item = item
    order.status = order_models.OrderStatus(status)
    return order


# ── generate_invoice tests ──────────────────────────────────────────────────


def test_generate_invoice_success():
    order = _make_order(status="received")
    invoice = _make_invoice()
    db = _make_db()
    order_repo = _make_mock_order_repo(order)
    invoice_repo = _make_mock_invoice_repo(invoice)
    invoice_repo.get_invoice_by_order_id.return_value = None
    invoice_repo.create_invoice.return_value = invoice

    with patch.object(service, '_call_payment_api_create_invoice', return_value='inv-test123'):
        with patch.object(service.order_service, 'update_order') as mock_update:
            result = service.generate_invoice(db, order_repo, invoice_repo, 1)

    assert result == invoice
    order_repo.create_order.assert_not_called()
    invoice_repo.create_invoice.assert_called_once_with(1, "inv-test123")
    mock_update.assert_called_once()


def test_generate_invoice_order_not_found():
    order_repo = _make_mock_order_repo(None)
    invoice_repo = _make_mock_invoice_repo()
    db = _make_db()

    try:
        service.generate_invoice(db, order_repo, invoice_repo, 999)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "Order not found"


def test_generate_invoice_order_not_received():
    order = _make_order(status="fulfilled")
    order_repo = _make_mock_order_repo(order)
    invoice_repo = _make_mock_invoice_repo()
    db = _make_db()

    try:
        service.generate_invoice(db, order_repo, invoice_repo, 1)
        assert False, "Should have raised PaymentError"
    except PaymentError as e:
        assert "Cannot generate invoice" in str(e)


def test_generate_invoice_already_exists():
    order = _make_order(status="received")
    invoice = _make_invoice()
    order_repo = _make_mock_order_repo(order)
    invoice_repo = _make_mock_invoice_repo(invoice)
    invoice_repo.get_invoice_by_order_id.return_value = invoice
    db = _make_db()

    try:
        service.generate_invoice(db, order_repo, invoice_repo, 1)
        assert False, "Should have raised PaymentError"
    except PaymentError as e:
        assert "already exists" in str(e)


# ── mark_invoice_paid tests ─────────────────────────────────────────────────


def test_mark_invoice_paid_success():
    order = _make_order()
    invoice = _make_invoice(status="pending")
    db = _make_db()
    order_repo = _make_mock_order_repo(order)
    invoice_repo = _make_mock_invoice_repo(invoice)
    invoice_repo.get_invoice.return_value = invoice
    invoice_repo.settle_invoice_and_advance_order.return_value = (invoice, order)

    result = service.mark_invoice_paid(db, invoice_repo, order_repo, 1)

    assert result == invoice
    invoice_repo.settle_invoice_and_advance_order.assert_called_once_with(1, 1, order_models.OrderStatus.FULFILLED)


def test_mark_invoice_paid_not_found():
    db = _make_db()
    order_repo = _make_mock_order_repo()
    invoice_repo = _make_mock_invoice_repo(None)
    invoice_repo.get_invoice.return_value = None

    try:
        service.mark_invoice_paid(db, invoice_repo, order_repo, 999)
        assert False, "Should have raised InvoiceNotFoundError"
    except InvoiceNotFoundError as e:
        assert "not found" in str(e)


def test_mark_invoice_paid_already_paid():
    invoice = _make_invoice(status="paid")
    db = _make_db()
    order_repo = _make_mock_order_repo()
    invoice_repo = _make_mock_invoice_repo(invoice)
    invoice_repo.get_invoice.return_value = invoice

    try:
        service.mark_invoice_paid(db, invoice_repo, order_repo, 1)
        assert False, "Should have raised PaymentError"
    except PaymentError as e:
        assert "already marked as paid" in str(e)


# ── mark_invoice_paid_by_order_id tests ─────────────────────────────────────


def test_mark_invoice_paid_by_order_id_success():
    order = _make_order()
    invoice = _make_invoice(status="pending")
    db = _make_db()
    order_repo = _make_mock_order_repo(order)
    invoice_repo = _make_mock_invoice_repo(invoice)
    invoice_repo.get_invoice_by_order_id.return_value = invoice
    invoice_repo.settle_invoice_and_advance_order.return_value = (invoice, order)

    result = service.mark_invoice_paid_by_order_id(db, invoice_repo, order_repo, 1)

    assert result == invoice
    invoice_repo.settle_invoice_and_advance_order.assert_called_once_with(1, 1, order_models.OrderStatus.FULFILLED)


def test_mark_invoice_paid_invoice_not_found():
    db = _make_db()
    order_repo = _make_mock_order_repo()
    invoice_repo = _make_mock_invoice_repo(None)
    invoice_repo.get_invoice_by_order_id.return_value = None

    try:
        service.mark_invoice_paid_by_order_id(db, invoice_repo, order_repo, 999)
        assert False, "Should have raised InvoiceNotFoundError"
    except InvoiceNotFoundError as e:
        assert "No invoice found" in str(e)


def test_mark_invoice_paid_already_paid():
    invoice = _make_invoice(status="paid")
    db = _make_db()
    order_repo = _make_mock_order_repo()
    invoice_repo = _make_mock_invoice_repo(invoice)
    invoice_repo.get_invoice_by_order_id.return_value = invoice

    try:
        service.mark_invoice_paid_by_order_id(db, invoice_repo, order_repo, 1)
        assert False, "Should have raised PaymentError"
    except PaymentError as e:
        assert "already marked as paid" in str(e)


# ── get_invoice tests ──────────────────────────────────────────────────────


def test_get_invoice_success():
    invoice = _make_invoice()
    invoice_repo = _make_mock_invoice_repo(invoice)
    invoice_repo.get_invoice.return_value = invoice

    result = service.get_invoice(invoice_repo, 1)
    assert result == invoice


def test_get_invoice_not_found():
    invoice_repo = _make_mock_invoice_repo(None)
    invoice_repo.get_invoice.return_value = None

    try:
        service.get_invoice(invoice_repo, 999)
        assert False, "Should have raised InvoiceNotFoundError"
    except InvoiceNotFoundError as e:
        assert "not found" in str(e)


# ── get_invoice_by_order tests ─────────────────────────────────────────────


def test_get_invoice_by_order_success():
    invoice = _make_invoice()
    invoice_repo = _make_mock_invoice_repo(invoice)
    invoice_repo.get_invoice_by_order_id.return_value = invoice

    result = service.get_invoice_by_order(invoice_repo, 1)
    assert result == invoice


def test_get_invoice_by_order_not_found():
    invoice_repo = _make_mock_invoice_repo(None)
    invoice_repo.get_invoice_by_order_id.return_value = None

    try:
        service.get_invoice_by_order(invoice_repo, 999)
        assert False, "Should have raised InvoiceNotFoundError"
    except InvoiceNotFoundError as e:
        assert "No invoice found" in str(e)


# ── list_invoices tests ────────────────────────────────────────────────────


def test_list_invoices():
    invoice_a = _make_invoice(order_id=1)
    invoice_b = _make_invoice(order_id=2)
    invoice_repo = _make_mock_invoice_repo(invoice_a)
    invoice_repo.list_invoices.return_value = ([invoice_a, invoice_b], 2)

    result, total = service.list_invoices(invoice_repo)
    assert len(result) == 2
    assert result[0].order_id == 1
    assert result[1].order_id == 2
    assert total == 2


# -- refund_invoice tests (issue 4) ---------------------------------------------

def test_refund_invoice_success():
    invoice = _make_invoice(status=payment_models.InvoiceStatus.PAID)
    order = _make_order(status="fulfilled")
    db = _make_db()
    result = service.refund_invoice(db, _make_mock_invoice_repo(invoice), _make_mock_order_repo(order), 1)
    assert result.status == payment_models.InvoiceStatus.CANCELLED
    assert order.status == order_models.OrderStatus.CANCELLED
    db.commit.assert_called_once()


def test_refund_invoice_rejects_unpaid():
    invoice = _make_invoice(status=payment_models.InvoiceStatus.PENDING)
    with pytest.raises(PaymentError):
        service.refund_invoice(_make_db(), _make_mock_invoice_repo(invoice), _make_mock_order_repo(_make_order()), 1)


def test_refund_invoice_not_found():
    with pytest.raises(InvoiceNotFoundError):
        service.refund_invoice(_make_db(), _make_mock_invoice_repo(None), _make_mock_order_repo(), 1)


def test_refund_invoice_shipped_order_is_invalid_transition():
    from app.modules.orders.service import InvalidOrderTransition
    invoice = _make_invoice(status=payment_models.InvoiceStatus.PAID)
    with pytest.raises(InvalidOrderTransition):
        service.refund_invoice(_make_db(), _make_mock_invoice_repo(invoice), _make_mock_order_repo(_make_order(status="shipped")), 1)
