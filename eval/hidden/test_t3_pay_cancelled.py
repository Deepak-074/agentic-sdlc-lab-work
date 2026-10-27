from unittest.mock import MagicMock
import pytest
from app.modules.payment import service, models as pm
from app.modules.payment.service import PaymentError

def test_cannot_pay_cancelled_invoice():
    inv = MagicMock(); inv.status = pm.InvoiceStatus.CANCELLED; inv.id = 1; inv.order_id = 2
    repo = MagicMock(); repo.get_invoice.return_value = inv; repo.get_invoice_by_order_id.return_value = inv
    with pytest.raises(PaymentError):
        service.mark_invoice_paid(MagicMock(), repo, MagicMock(), 1)
    with pytest.raises(PaymentError):
        service.mark_invoice_paid_by_order_id(MagicMock(), repo, MagicMock(), 2)
