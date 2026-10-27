from unittest.mock import MagicMock
import pytest

from app.modules.orders import service, repository, models
from app.modules.orders.service import OrderStateMachine, InvalidOrderTransition
from app.modules.orders.exceptions import OrderOwnershipError


def _make_mock_repo(order=None):
    repo = MagicMock(spec=repository.OrderRepository)
    repo._db = MagicMock()
    repo.get_order.return_value = order
    return repo


def _make_db():
    db = MagicMock()
    return db


def _make_order(item="widget", status="received"):
    order = MagicMock(spec=models.Order)
    order.id = 1
    order.item = item
    order.status = status
    return order


def test_create_order():
    repo = _make_mock_repo()
    result = service.create_order(repo, 1, "laptop")
    repo.create_order.assert_called_once_with(1, "laptop")
    assert result == repo.create_order.return_value


def test_get_order():
    order = _make_order()
    repo = _make_mock_repo(order=order)
    result = service.get_order(repo, 1)
    assert result == order


def test_get_order_not_found():
    repo = _make_mock_repo(order=None)
    try:
        service.get_order(repo, 999)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "Order not found"


def test_list_orders():
    repo = _make_mock_repo()
    repo.list_orders.return_value = ([_make_order("a"), _make_order("b")], 2)
    result, total = service.list_orders(repo)
    assert len(result) == 2
    assert result[0].item == "a"
    assert result[1].item == "b"
    assert total == 2


def test_update_order_status():
    order = _make_order()
    repo = _make_mock_repo(order=order)
    db = _make_db()
    result = service.update_order(db, repo, 1, status="processing")
    assert result.status == "processing"
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(order)


def test_update_order_item():
    order = _make_order()
    repo = _make_mock_repo(order=order)
    db = _make_db()
    result = service.update_order(db, repo, 1, item="new_item")
    assert result.item == "new_item"
    assert result.status == "received"


def test_update_order_not_found():
    repo = _make_mock_repo(order=None)
    db = _make_db()
    try:
        service.update_order(db, repo, 999, status="shipped")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "Order not found"


def test_delete_order():
    order = _make_order()
    repo = _make_mock_repo(order=order)
    db = _make_db()
    service.delete_order(db, repo, 1)
    repo.delete_order.assert_called_once_with(1)
    db.commit.assert_called_once()


def test_delete_order_not_found():
    repo = _make_mock_repo(order=None)
    db = _make_db()
    try:
        service.delete_order(db, repo, 999)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "Order not found"


# ── FSM Unit Tests ──────────────────────────────────────────────────────────

VALID_TRANSITIONS = [
    (models.OrderStatus.RECEIVED, models.OrderStatus.PROCESSING),
    (models.OrderStatus.RECEIVED, models.OrderStatus.CANCELLED),
    (models.OrderStatus.PROCESSING, models.OrderStatus.FULFILLED),
    (models.OrderStatus.PROCESSING, models.OrderStatus.CANCELLED),
    (models.OrderStatus.FULFILLED, models.OrderStatus.SHIPPED),
    (models.OrderStatus.FULFILLED, models.OrderStatus.CANCELLED),
    (models.OrderStatus.SHIPPED, models.OrderStatus.DELIVERED),
]

INVALID_TRANSITIONS = [
    (models.OrderStatus.RECEIVED, models.OrderStatus.FULFILLED),
    (models.OrderStatus.RECEIVED, models.OrderStatus.SHIPPED),
    (models.OrderStatus.RECEIVED, models.OrderStatus.DELIVERED),
    (models.OrderStatus.PROCESSING, models.OrderStatus.SHIPPED),
    (models.OrderStatus.PROCESSING, models.OrderStatus.DELIVERED),
    (models.OrderStatus.FULFILLED, models.OrderStatus.DELIVERED),
    (models.OrderStatus.FULFILLED, models.OrderStatus.RECEIVED),
    (models.OrderStatus.SHIPPED, models.OrderStatus.PROCESSING),
    (models.OrderStatus.SHIPPED, models.OrderStatus.CANCELLED),
    (models.OrderStatus.DELIVERED, models.OrderStatus.PROCESSING),
    (models.OrderStatus.DELIVERED, models.OrderStatus.DELIVERED),
    (models.OrderStatus.CANCELLED, models.OrderStatus.PROCESSING),
    (models.OrderStatus.CANCELLED, models.OrderStatus.CANCELLED),
]


@pytest.mark.parametrize("current, target", VALID_TRANSITIONS)
def test_fsm_valid_transitions(current, target):
    OrderStateMachine.validate_transition(current, target)


@pytest.mark.parametrize("current, target", INVALID_TRANSITIONS)
def test_fsm_invalid_transitions(current, target):
    with pytest.raises(InvalidOrderTransition):
        OrderStateMachine.validate_transition(current, target)


def test_fsm_unknown_current_status():
    with pytest.raises(InvalidOrderTransition):
        OrderStateMachine.validate_transition("unknown", models.OrderStatus.PROCESSING)


def test_fsm_unknown_target_status():
    with pytest.raises(InvalidOrderTransition):
        OrderStateMachine.validate_transition(models.OrderStatus.RECEIVED, "unknown")


# ── Service Layer FSM Integration Tests ─────────────────────────────────────


def test_update_order_invalid_status_transition():
    order = _make_order()
    repo = _make_mock_repo(order=order)
    db = _make_db()
    with pytest.raises(InvalidOrderTransition):
        service.update_order(db, repo, 1, status="delivered")
    db.commit.assert_not_called()
    db.refresh.assert_not_called()


def test_update_order_valid_status_transition():
    order = _make_order()
    repo = _make_mock_repo(order=order)
    db = _make_db()
    result = service.update_order(db, repo, 1, status="processing")
    assert result.status == "processing"
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(order)


# -- cancel_order tests (issue 2) ------------------------------------------------

def test_cancel_order_success():
    order = _make_order(status=models.OrderStatus.PROCESSING)
    db = _make_db()
    result = service.cancel_order(db, _make_mock_repo(order=order), 1)
    assert result.status == models.OrderStatus.CANCELLED
    db.commit.assert_called_once()


def test_cancel_order_rejects_delivered():
    order = _make_order(status=models.OrderStatus.DELIVERED)
    db = _make_db()
    with pytest.raises(OrderOwnershipError, match="delivered"):
        service.cancel_order(db, _make_mock_repo(order=order), 1)
    assert order.status == models.OrderStatus.DELIVERED
    db.commit.assert_not_called()


def test_cancel_order_rejects_already_cancelled():
    order = _make_order(status=models.OrderStatus.CANCELLED)
    with pytest.raises(OrderOwnershipError, match="already cancelled"):
        service.cancel_order(_make_db(), _make_mock_repo(order=order), 1)
