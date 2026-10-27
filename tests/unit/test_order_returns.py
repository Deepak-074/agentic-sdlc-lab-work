from unittest.mock import MagicMock
import pytest

from app.modules.orders import service, repository, models
from app.modules.orders.exceptions import OrderOwnershipError
from app.modules.orders.service import OrderStateMachine


def test_delivered_can_be_returned():
    OrderStateMachine.validate_transition(models.OrderStatus.DELIVERED, models.OrderStatus.RETURNED)


def test_returned_is_terminal():
    assert OrderStateMachine.TRANSITIONS[models.OrderStatus.RETURNED] == []


def test_cancel_order_rejects_returned():
    order = MagicMock(spec=models.Order)
    order.status = models.OrderStatus.RETURNED
    repo = MagicMock(spec=repository.OrderRepository)
    repo.get_order.return_value = order
    with pytest.raises(OrderOwnershipError, match="returned"):
        service.cancel_order(MagicMock(), repo, 1)
