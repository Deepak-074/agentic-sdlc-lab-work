from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import service, schemas, models as order_models
from .exceptions import OrderNotFoundError, OrderOwnershipError
from .service import InvalidOrderTransition
from app.core.auth import get_current_user
from app.core import dependencies as deps
from app.db.session import get_db
from app.modules.users.models import User as UserModel

router = APIRouter()


def get_current_user_obj(
    username: str = Depends(get_current_user),
    user_repo: deps.UserRepository = Depends(deps.get_users_repository),
) -> UserModel:
    user = user_repo.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=schemas.OrderRead)
def create_order(
    payload: schemas.OrderCreate,
    db: Session = Depends(get_db),
    repo: deps.OrderRepository = Depends(deps.get_orders_repository),
    user: UserModel = Depends(get_current_user_obj),
):
    return service.create_order(repo, user.id, payload.item)


@router.get("/{order_id}", response_model=schemas.OrderRead)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    repo: deps.OrderRepository = Depends(deps.get_orders_repository),
    user: UserModel = Depends(get_current_user_obj),
):
    try:
        order = service.require_order_ownership(repo, order_id, user.id)
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except OrderOwnershipError:
        raise HTTPException(status_code=403, detail="Access denied")
    return order


@router.get("/", response_model=schemas.PaginatedOrders)
def list_orders(
    page: int = 1,
    page_size: int = 20,
    status: order_models.OrderStatus | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    repo: deps.OrderRepository = Depends(deps.get_orders_repository),
    user: UserModel = Depends(get_current_user_obj),
):
    items, total = service.list_orders(repo, user_id=user.id, status=status, search=search, page=page, page_size=page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.put("/{order_id}", response_model=schemas.OrderRead)
def update_order(
    order_id: int,
    payload: schemas.OrderUpdate,
    db: Session = Depends(get_db),
    repo: deps.OrderRepository = Depends(deps.get_orders_repository),
    user: UserModel = Depends(get_current_user_obj),
):
    try:
        service.require_order_ownership(repo, order_id, user.id)
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except OrderOwnershipError:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
        return service.update_order(db, repo, order_id, **updates)
    except InvalidOrderTransition as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/cancel", response_model=schemas.OrderRead)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    repo: deps.OrderRepository = Depends(deps.get_orders_repository),
    payment_repo: deps.InvoiceRepository = Depends(deps.get_payment_repository),
    user: UserModel = Depends(get_current_user_obj),
):
    try:
        order = service.cancel_order_with_invoice(db, repo, payment_repo, order_id)
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except OrderOwnershipError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return order


@router.delete("/{order_id}", status_code=204)
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    repo: deps.OrderRepository = Depends(deps.get_orders_repository),
    user: UserModel = Depends(get_current_user_obj),
):
    try:
        service.require_order_ownership(repo, order_id, user.id)
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except OrderOwnershipError:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        service.delete_order(db, repo, order_id)
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")


@router.get("/{order_id}/history", response_model=list[schemas.OrderHistoryRead])
def get_order_history(
    order_id: int,
    db: Session = Depends(get_db),
    repo: deps.OrderRepository = Depends(deps.get_orders_repository),
    user: UserModel = Depends(get_current_user_obj),
):
    try:
        service.require_order_ownership(repo, order_id, user.id)
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except OrderOwnershipError:
        raise HTTPException(status_code=403, detail="Access denied")
    return service.get_order_history(repo, order_id)
