from unittest.mock import MagicMock
from app.modules.orders import service, repository

def test_list_orders_caps_page_size_and_floors_page():
    repo = MagicMock(spec=repository.OrderRepository); repo.list_orders.return_value = ([], 0)
    service.list_orders(repo, page_size=500, page=0)
    kw = repo.list_orders.call_args.kwargs
    assert kw["page_size"] == 100 and kw["page"] == 1
