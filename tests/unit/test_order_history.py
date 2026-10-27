from unittest.mock import MagicMock
import pytest

from app.modules.orders import service, repository, models
from app.modules.orders.exceptions import OrderNotFoundError
from app.modules.payment import service as payment_service, models as payment_models
from app.modules.payment import repository as payment_repository


def _repo(order=None):
    repo = MagicMock(spec=repository.OrderRepository)
    repo.get_order.return_value = order
    return repo


def _order(status):
    order = MagicMock(spec=models.Order)
    order.id = 1
    order.status = status
    return order


def test_update_order_records_history():
    repo = _repo(_order(models.OrderStatus.RECEIVED))
    service.update_order(MagicMock(), repo, 1, status=models.OrderStatus.PROCESSING)
    repo.add_history.assert_called_once_with(1, models.OrderStatus.PROCESSING)


def test_update_order_without_status_records_nothing():
    repo = _repo(_order(models.OrderStatus.RECEIVED))
    service.update_order(MagicMock(), repo, 1, item="gadget")
    repo.add_history.assert_not_called()


def test_cancel_order_records_history():
    repo = _repo(_order(models.OrderStatus.PROCESSING))
    service.cancel_order(MagicMock(), repo, 1)
    repo.add_history.assert_called_once_with(1, models.OrderStatus.CANCELLED)


def test_get_order_history_returns_rows():
    repo = _repo(_order(models.OrderStatus.RECEIVED))
    repo.list_history.return_value = ["row1", "row2"]
    assert service.get_order_history(repo, 1) == ["row1", "row2"]


def test_get_order_history_not_found():
    with pytest.raises(OrderNotFoundError):
        service.get_order_history(_repo(None), 1)


def test_refund_records_history_through_the_orders_repository():
    invoice = MagicMock(spec=payment_models.Invoice)
    invoice.status = payment_models.InvoiceStatus.PAID
    invoice_repo = MagicMock(spec=payment_repository.InvoiceRepository)
    invoice_repo.get_invoice_by_order_id.return_value = invoice
    order_repo = _repo(_order(models.OrderStatus.FULFILLED))
    payment_service.refund_invoice(MagicMock(), invoice_repo, order_repo, 1)
    order_repo.add_history.assert_called_once_with(1, models.OrderStatus.CANCELLED)
