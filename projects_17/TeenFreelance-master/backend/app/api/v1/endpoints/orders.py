from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
from decimal import Decimal
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.order import OrderStatus, Order
from app.crud import order as crud_order
from app.schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderListResponse

router = APIRouter()


@router.get("", response_model=OrderListResponse)
def read_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    category_id: Optional[str] = None,
    subcategory_id: Optional[str] = None,
    subsubcategory_id: Optional[str] = None,
    # Массивы ID для фильтрации по всей иерархии
    # Квадратные скобки [] — чтобы axios отправлял массивы корректно
    category_ids: Optional[List[str]] = Query(None, alias="category_ids[]", description="Список ID корневых категорий"),
    subcategory_ids: Optional[List[str]] = Query(None, alias="subcategory_ids[]", description="Список ID подкатегорий"),
    subsubcategory_ids: Optional[List[str]] = Query(None, alias="subsubcategory_ids[]", description="Список ID под-подкатегорий"),
    budget_from: Optional[Decimal] = None,
    budget_to: Optional[Decimal] = None,
    keywords: Optional[str] = None,
    status: Optional[OrderStatus] = None,
    min_hired_percent: Optional[float] = Query(None, ge=0, le=100, description="Минимальный процент найма заказчика"),
    offers_count_from: Optional[int] = Query(None, ge=0, description="Минимальное количество откликов"),
    offers_count_to: Optional[int] = Query(None, ge=0, description="Максимальное количество откликов"),
    db: Session = Depends(get_db)
):
    """Получение списка заказов с фильтрами"""
    items, total = crud_order.order.get_multi_with_filters(
        db,
        skip=skip,
        limit=limit,
        category_id=category_id,
        subcategory_id=subcategory_id,
        subsubcategory_id=subsubcategory_id,
        category_ids=category_ids,
        subcategory_ids=subcategory_ids,
        subsubcategory_ids=subsubcategory_ids,
        budget_from=budget_from,
        budget_to=budget_to,
        keywords=keywords,
        status=status,
        min_hired_percent=min_hired_percent,
        offers_count_from=offers_count_from,
        offers_count_to=offers_count_to,
    )
    # Загружаем связанных заказчиков и подсчитываем предложения
    from sqlalchemy.orm import joinedload
    from app.models.offer import Offer
    from app.models.order import Order
    from sqlalchemy import func
    
    if not items:
        return OrderListResponse(items=[], total=0, page=skip // limit + 1, page_size=limit)
    
    # Загружаем заказы с заказчиками
    order_ids = [item.id for item in items]
    items_with_customers = db.query(Order).options(joinedload(Order.customer)).filter(
        Order.id.in_(order_ids)
    ).all()
    
    # Подсчитываем предложения для каждого заказа
    offers_counts = {}
    offers_query = db.query(Offer.order_id, func.count(Offer.id).label('count')).filter(
        Offer.order_id.in_(order_ids)
    ).group_by(Offer.order_id).all()
    offers_counts = {order_id: count for order_id, count in offers_query}

    # Собираем уникальных заказчиков для batch-запроса статистики
    customer_ids = list(set(item.customer_id for item in items_with_customers if item.customer_id))

    # Статистика заказчиков: сколько всего заказов + сколько завершённых
    customer_stats = {}  # customer_id -> {total: int, completed: int}
    if customer_ids:
        # Всего заказов по каждому заказчику
        total_orders_query = db.query(
            Order.customer_id,
            func.count(Order.id).label('total')
        ).filter(
            Order.customer_id.in_(customer_ids)
        ).group_by(Order.customer_id).all()
        for cid, total in total_orders_query:
            customer_stats[cid] = {'total': total, 'completed': 0}

        # Завершённых заказов по каждому заказчику
        completed_orders_query = db.query(
            Order.customer_id,
            func.count(Order.id).label('completed')
        ).filter(
            Order.customer_id.in_(customer_ids),
            Order.status == OrderStatus.completed
        ).group_by(Order.customer_id).all()
        for cid, completed in completed_orders_query:
            if cid in customer_stats:
                customer_stats[cid]['completed'] = completed

    # Формируем результат с дополнительными полями
    result_items = []
    for item in items_with_customers:
        offers_count = offers_counts.get(item.id, 0)
        stats = customer_stats.get(item.customer_id, {'total': 0, 'completed': 0})
        hired_percent = round((stats['completed'] / stats['total'] * 100), 1) if stats['total'] > 0 else 0.0

        order_data = {
            "id": item.id,
            "customer_id": item.customer_id,
            "title": item.title,
            "description": item.description,
            "category_id": item.category_id,
            "subcategory_id": item.subcategory_id,
            "subsubcategory_id": item.subsubcategory_id,
            "budget_from": item.budget_from,
            "budget_to": item.budget_to,
            "allow_higher_price": item.allow_higher_price,
            "deadline": item.deadline,
            "status": item.status,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "files": item.files,
            "skills": item.skills,
            "customer_name": item.customer.name if item.customer else None,
            "customer_avatar_url": item.customer.avatar_url if item.customer else None,
            "offers_count": offers_count,
            "customer_projects_count": stats['total'],
            "customer_hired_percent": hired_percent
        }
        result_items.append(OrderResponse(**order_data))
    
    return OrderListResponse(items=result_items, total=total, page=skip // limit + 1, page_size=limit)


@router.get("/my", response_model=OrderListResponse)
def read_my_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[OrderStatus] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Получение заказов текущего пользователя (как заказчика)"""
    items, total = crud_order.order.get_multi_with_filters(
        db,
        skip=skip,
        limit=limit,
        customer_id=current_user.id,
        status=status
    )
    return OrderListResponse(items=items, total=total, page=skip // limit + 1, page_size=limit)


@router.get("/my-executor", response_model=OrderListResponse)
def read_my_executor_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[OrderStatus] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Получение заказов текущего пользователя (как исполнителя)"""
    from app.models.offer import Offer, OfferStatus
    from app.models.order import Order
    from sqlalchemy.orm import joinedload
    from sqlalchemy import and_
    
    # Находим все принятые офферы текущего пользователя
    accepted_offers = db.query(Offer).filter(
        and_(
            Offer.executor_id == current_user.id,
            Offer.status == OfferStatus.accepted
        )
    ).all()
    
    if not accepted_offers:
        return OrderListResponse(items=[], total=0, page=skip // limit + 1, page_size=limit)
    
    # Получаем ID заказов из офферов
    order_ids = [offer.order_id for offer in accepted_offers]
    
    # Загружаем заказы с заказчиками
    query = db.query(Order).options(joinedload(Order.customer)).filter(
        Order.id.in_(order_ids)
    )
    
    # Фильтруем по статусу если указан
    if status:
        query = query.filter(Order.status == status)
    # Если статус не указан, показываем все заказы с принятыми офферами (включая IN_PROGRESS, COMPLETED, CANCELLED)
    # Не показываем только DRAFT статус
    
    total = query.count()
    items = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    
    return OrderListResponse(items=items, total=total, page=skip // limit + 1, page_size=limit)


@router.get("/{order_id}", response_model=OrderResponse)
def read_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    """Получение заказа по ID"""
    order = crud_order.order.get(db, id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return order


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_in: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Создание нового заказа/проекта"""
    # Проверка на дубликаты (защита от двойного клика)
    check_time = datetime.utcnow() - timedelta(minutes=2)
    duplicate = db.query(Order).filter(
        Order.customer_id == current_user.id,
        Order.title == order_in.title,
        Order.description == order_in.description,
        Order.created_at >= check_time
    ).first()

    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы уже создали такой заказ. Пожалуйста, подождите."
        )

    return crud_order.order.create_with_skills(
        db, obj_in=order_in, customer_id=current_user.id
    )


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: int,
    order_in: OrderUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Обновление заказа"""
    order = crud_order.order.get(db, id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    if order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return crud_order.order.update_with_skills(db, db_obj=order, obj_in=order_in)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Удаление заказа (только если статус OPEN - ожидает откликов)"""
    order = crud_order.order.get(db, id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    if order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    # Проверяем, что заказ в статусе OPEN (ожидает откликов)
    if order.status != OrderStatus.open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete order with status {order.status}. Only orders with status 'open' (awaiting responses) can be deleted."
        )
    crud_order.order.remove(db, id=order_id)
    return None


@router.post("/{order_id}/complete", response_model=OrderResponse)
def complete_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Завершение заказа (может выполнить заказчик или исполнитель)"""
    from sqlalchemy.orm import joinedload
    from app.models.offer import Offer, OfferStatus
    
    order = db.query(Order).options(joinedload(Order.customer)).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Проверяем права: заказчик или исполнитель
    is_customer = order.customer_id == current_user.id
    is_executor = False
    
    if not is_customer:
        # Проверяем, является ли пользователь исполнителем
        accepted_offer = db.query(Offer).filter(
            Offer.order_id == order_id,
            Offer.executor_id == current_user.id,
            Offer.status == OfferStatus.accepted
        ).first()
        is_executor = accepted_offer is not None
    
    if not (is_customer or is_executor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only order customer or executor can complete it"
        )
    
    # Проверяем, что заказ в работе или на проверке
    if order.status not in [OrderStatus.in_progress, OrderStatus.review]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order must be in progress or review. Current status: {order.status}"
        )
    
    # Меняем статус на завершен
    order.status = OrderStatus.completed
    db.commit()
    db.refresh(order)
    
    return order


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Отмена заказа (может выполнить заказчик или исполнитель)"""
    from sqlalchemy.orm import joinedload
    from app.models.offer import Offer, OfferStatus
    
    order = db.query(Order).options(joinedload(Order.customer)).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Проверяем права: заказчик или исполнитель
    is_customer = order.customer_id == current_user.id
    is_executor = False
    
    if not is_customer:
        # Проверяем, является ли пользователь исполнителем
        accepted_offer = db.query(Offer).filter(
            Offer.order_id == order_id,
            Offer.executor_id == current_user.id,
            Offer.status == OfferStatus.accepted
        ).first()
        is_executor = accepted_offer is not None
    
    if not (is_customer or is_executor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only order customer or executor can cancel it"
        )
    
    # Проверяем, что заказ не уже завершен или отменен
    if order.status in [OrderStatus.completed, OrderStatus.cancelled]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order with status: {order.status}"
        )
    
    # Меняем статус на отменен
    order.status = OrderStatus.cancelled
    db.commit()
    db.refresh(order)
    
    return order


@router.post("/{order_id}/submit-for-review", response_model=OrderResponse)
def submit_order_for_review(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Сдача работы исполнителем на проверку заказчику (как на Kwork)"""
    from sqlalchemy.orm import joinedload
    from app.models.offer import Offer, OfferStatus
    from app.models.message import Message, MessageType
    
    order = db.query(Order).options(joinedload(Order.customer)).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Проверяем, что текущий пользователь - исполнитель
    accepted_offer = db.query(Offer).filter(
        Offer.order_id == order_id,
        Offer.executor_id == current_user.id,
        Offer.status == OfferStatus.accepted
    ).first()
    
    if not accepted_offer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only order executor can submit work for review"
        )
    
    # Проверяем, что заказ в работе
    if order.status != OrderStatus.in_progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order must be in progress. Current status: {order.status}"
        )
    
    # Меняем статус на "на проверке".
    # Статусы в БД хранятся в enum orderstatus; используем прямой SQL, чтобы не упираться в особенности Enum.
    from sqlalchemy import text
    # Нормализуем текущее значение статуса к верхнему регистру строки
    current_status = str(getattr(order, "status", "")).upper()
    if current_status == "review":
        # Заказ уже на проверке — повторно не меняем
        return order

    try:
        db.execute(
            text("UPDATE orders SET status = 'review', updated_at = now() WHERE id = :order_id"),
            {"order_id": order_id},
        )
        db.commit()
        db.refresh(order)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating order status to REVIEW: {str(e)}"
        )
    
    # Создаем уведомление заказчику о сдаче работы через "сырой" SQL,
    # чтобы не упираться в несоответствие Python Enum и PostgreSQL enum.
    from sqlalchemy import text

    content = f"""✅ Исполнитель {current_user.name} сдал работу на проверку

━━━━━━━━━━━━━━━━━━━━━━
Заказ: '{order.title}'
Проверьте выполненную работу и примите её или запросите доработку."""

    try:
        db.execute(
            text(
                """
                INSERT INTO messages (
                    from_user_id,
                    to_user_id,
                    offer_id,
                    order_id,
                    message_type,
                    title,
                    content,
                    is_read
                )
                VALUES (
                    :from_user_id,
                    :to_user_id,
                    :offer_id,
                    :order_id,
                    :message_type,
                    :title,
                    :content,
                    :is_read
                )
                """
            ),
            {
                "from_user_id": current_user.id,
                "to_user_id": order.customer_id,
                "offer_id": accepted_offer.id,
                "order_id": order.id,
                # В PostgreSQL enum messagetype использует нижний регистр 'text'
                "message_type": "text",
                "title": f"Работа по заказу '{order.title}' сдана на проверку",
                "content": content,
                "is_read": False,
            },
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating review notification message: {str(e)}",
        )

    return order


@router.post("/{order_id}/accept-work", response_model=OrderResponse)
def accept_work(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Принятие работы заказчиком (завершение заказа)"""
    from sqlalchemy.orm import joinedload
    from app.models.offer import Offer, OfferStatus
    from app.models.message import Message, MessageType
    
    order = db.query(Order).options(joinedload(Order.customer)).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Проверяем, что текущий пользователь - заказчик
    if order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only order customer can accept work"
        )
    
    # Проверяем, что заказ на проверке
    if order.status != OrderStatus.review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order must be in review. Current status: {order.status}"
        )
    
    # Находим исполнителя через принятый оффер
    accepted_offer = db.query(Offer).filter(
        Offer.order_id == order_id,
        Offer.status == OfferStatus.accepted
    ).first()
    
    if not accepted_offer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Accepted offer not found"
        )
    
    # Меняем статус на завершен
    order.status = OrderStatus.completed
    db.commit()
    db.refresh(order)
    
    # Создаем уведомление исполнителю
    content = f"""✅ Заказчик принял вашу работу!

━━━━━━━━━━━━━━━━━━━━━━
Заказ: '{order.title}'
Работа принята. Заказ завершен."""
    
    msg = Message(
        from_user_id=current_user.id,
        to_user_id=accepted_offer.executor_id,
        message_type=MessageType.text,
        title=f"Заказ '{order.title}' принят",
        content=content,
        order_id=order.id,
        offer_id=accepted_offer.id
    )
    db.add(msg)
    db.commit()
    
    return order


@router.post("/{order_id}/request-revision", response_model=OrderResponse)
def request_revision(
    order_id: int,
    revision_comment: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Запрос доработки работы заказчиком (возврат в работу)"""
    from sqlalchemy.orm import joinedload
    from app.models.offer import Offer, OfferStatus
    from app.models.message import Message, MessageType
    
    order = db.query(Order).options(joinedload(Order.customer)).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Проверяем, что текущий пользователь - заказчик
    if order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only order customer can request revision"
        )
    
    # Проверяем, что заказ на проверке
    if order.status != OrderStatus.review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order must be in review. Current status: {order.status}"
        )
    
    # Находим исполнителя через принятый оффер
    accepted_offer = db.query(Offer).filter(
        Offer.order_id == order_id,
        Offer.status == OfferStatus.accepted
    ).first()
    
    if not accepted_offer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Accepted offer not found"
        )
    
    # Возвращаем статус в "в работе" для доработки
    order.status = OrderStatus.in_progress
    db.commit()
    db.refresh(order)
    
    # Создаем уведомление исполнителю
    comment_text = f"\n\nКомментарий заказчика:\n{revision_comment}" if revision_comment else ""
    content = f"""⚠️ Заказчик запросил доработку

━━━━━━━━━━━━━━━━━━━━━━
Заказ: '{order.title}'
Пожалуйста, внесите необходимые изменения.{comment_text}"""
    
    msg = Message(
        from_user_id=current_user.id,
        to_user_id=accepted_offer.executor_id,
        message_type=MessageType.text,
        title=f"Требуется доработка по заказу '{order.title}'",
        content=content,
        order_id=order.id,
        offer_id=accepted_offer.id
    )
    db.add(msg)
    db.commit()
    
    return order
