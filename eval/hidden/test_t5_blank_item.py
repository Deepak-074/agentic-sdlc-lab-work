from unittest.mock import MagicMock
import pytest
from app.modules.orders import service, repository

def test_create_order_rejects_blank_item():
    repo = MagicMock(spec=repository.OrderRepository)
    with pytest.raises(ValueError):
        service.create_order(repo, 1, "   ")
    repo.create_order.assert_not_called()
