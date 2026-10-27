from unittest.mock import MagicMock
import pytest
from app.modules.orders import service, repository, models
from app.modules.orders.exceptions import OrderOwnershipError

def test_cancel_rejects_delivered():
    repo = MagicMock(spec=repository.OrderRepository)
    order = MagicMock(spec=models.Order); order.status = models.OrderStatus.DELIVERED
    repo.get_order.return_value = order
    with pytest.raises(OrderOwnershipError):
        service.cancel_order(MagicMock(), repo, 1)
