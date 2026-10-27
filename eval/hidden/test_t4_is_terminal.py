from app.modules.orders import models
from app.modules.orders.service import OrderStateMachine

def test_is_terminal():
    S = models.OrderStatus
    assert OrderStateMachine.is_terminal(S.DELIVERED) and OrderStateMachine.is_terminal(S.CANCELLED)
    assert not OrderStateMachine.is_terminal(S.SHIPPED)
