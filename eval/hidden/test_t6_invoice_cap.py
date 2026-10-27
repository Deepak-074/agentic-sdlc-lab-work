from unittest.mock import MagicMock
from app.modules.payment import service

def test_list_invoices_caps_page_size_and_floors_page():
    repo = MagicMock(); repo.list_invoices.return_value = ([], 0)
    service.list_invoices(repo, page_size=500, page=0)
    kw = repo.list_invoices.call_args.kwargs
    assert kw["page_size"] == 100 and kw["page"] == 1
