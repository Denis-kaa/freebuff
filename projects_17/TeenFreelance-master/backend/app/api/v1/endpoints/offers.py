from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.crud import offer as crud_offer, order as crud_order, message as crud_message
from app.schemas.offer import OfferCreate, OfferUpdate, OfferResponse
from app.models.message import MessageType
from app.schemas.message import MessageCreate

router = APIRouter()


@router.post("", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
def create_offer(
    offer_in: OfferCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Создание предложения на заказ"""
    # Проверяем существование заказа
    if not offer_in.order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="order_id is required"
        )
    
    order = crud_order.order.get(db, id=offer_in.order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Запрещаем откликаться на собственные заказы
    if order.customer_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot bid on your own project"
        )
    
    # Создаем предложение
    offer = crud_offer.offer.create_with_stages(
        db, obj_in=offer_in, executor_id=current_user.id
    )
    
    # Перезагружаем офер со связанными данными
    db.refresh(offer)
    # Загружаем этапы если они есть
    if offer.payment_type.value == "stages":
        from sqlalchemy.orm import joinedload
        from app.models.offer import Offer
        offer = db.query(Offer).options(joinedload(Offer.stages)).filter(Offer.id == offer.id).first()
    
    # Создаем сообщение заказчику
    payment_type_text = "По этапам" if offer.payment_type.value == "stages" else "Сразу после завершения"
    stages_text = ""
    if offer.stages and len(offer.stages) > 0:
        stages_text = "\n\nЭтапы:\n" + "\n".join([
            f"  • {stage.name}: {float(stage.price):,.0f} ₽"
            for stage in offer.stages
        ])
    
    deadline_text = ""
    if offer.deadline:
        from datetime import datetime, timezone
        try:
            now = datetime.now(timezone.utc)
            if offer.deadline.tzinfo:
                deadline_days = (offer.deadline - now).days
            else:
                # Если deadline без timezone, считаем что это UTC
                deadline_days = (offer.deadline.replace(tzinfo=timezone.utc) - now).days
            if deadline_days > 0:
                deadline_text = f"\n⏱️ Срок: {deadline_days} дней"
        except Exception:
            # Если ошибка при вычислении, просто пропускаем
            pass
    
    content = f"""📢 Новый отклик на проект "{order.title}"

━━━━━━━━━━━━━━━━━━━━━━
Исполнитель: {current_user.name}
💰 Сумма: {float(offer.total_price):,.0f} ₽
{deadline_text}
📊 Оплата: {payment_type_text}
{stages_text}

Описание предложения:
{offer.description}"""
    
    message = MessageCreate(
        message_type=MessageType.OFFER_CREATED,
        title=f"Новый отклик на проект '{order.title}'",
        content=content,
        offer_id=offer.id,
        order_id=order.id,
        to_user_id=order.customer_id
    )
    
    # Создаем сообщение с указанием from_user_id
    from app.models.message import Message
    message_obj = Message(
        from_user_id=current_user.id,
        to_user_id=order.customer_id,
        message_type=MessageType.OFFER_CREATED,
        title=message.title,
        content=message.content,
        offer_id=message.offer_id,
        order_id=message.order_id
    )
    db.add(message_obj)
    db.commit()
    db.refresh(message_obj)
    
    return offer


@router.get("/orders/{order_id}", response_model=List[OfferResponse])
def read_offers_by_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    """Получение всех предложений на заказ"""
    return crud_offer.offer.get_by_order_id(db, order_id=order_id)


@router.get("/my", response_model=List[OfferResponse])
def read_my_offers(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Получение предложений текущего пользователя"""
    return crud_offer.offer.get_by_executor_id(db, executor_id=current_user.id)


@router.get("/{offer_id}", response_model=OfferResponse)
def read_offer(
    offer_id: int,
    db: Session = Depends(get_db)
):
    """Получение предложения по ID"""
    offer = crud_offer.offer.get(db, id=offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found"
        )
    return offer


@router.put("/{offer_id}", response_model=OfferResponse)
def update_offer(
    offer_id: int,
    offer_in: OfferUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Обновление предложения"""
    offer = crud_offer.offer.get(db, id=offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found"
        )
    if offer.executor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return crud_offer.offer.update_with_stages(db, db_obj=offer, obj_in=offer_in)


@router.delete("/{offer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_offer(
    offer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Удаление предложения"""
    offer = crud_offer.offer.get(db, id=offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found"
        )
    if offer.executor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    crud_offer.offer.remove(db, id=offer_id)
    return None


@router.post("/{offer_id}/accept", response_model=OfferResponse)
def accept_offer(
    offer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Принятие предложения заказчиком"""
    offer = crud_offer.offer.get(db, id=offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found"
        )
    
    order = crud_order.order.get(db, id=offer.order_id)
    if order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only order owner can accept offers"
        )
    
    from app.models.offer import OfferStatus
    offer_in = OfferUpdate(status=OfferStatus.accepted)
    offer = crud_offer.offer.update(db, db_obj=offer, obj_in=offer_in)
    
    # Создаем сообщение исполнителю об одобрении
    payment_type_text = "По этапам" if offer.payment_type.value == "stages" else "Сразу после завершения"
    stages_text = ""
    if offer.stages:
        stages_text = "\n\nЭтапы:\n" + "\n".join([
            f"  • {stage.name}: {float(stage.price):,.0f} ₽"
            for stage in offer.stages
        ])
    
    deadline_text = ""
    if offer.deadline:
        from datetime import datetime
        deadline_days = (offer.deadline - datetime.now(offer.deadline.tzinfo)).days
        deadline_text = f"\n⏱️ Срок: {deadline_days} дней"
    
    content = f"""✅ Ваше предложение одобрено! Заказчик {current_user.name} одобрил ваш отклик на проект '{order.title}'

━━━━━━━━━━━━━━━━━━━━━━
💰 Сумма: {float(offer.total_price):,.0f} ₽
{deadline_text}
📊 Оплата: {payment_type_text}
{stages_text}

Теперь вы можете принять заказ и начать работу."""
    
    # Создаем сообщение напрямую через модель
    from app.models.message import Message
    message_obj = Message(
        from_user_id=current_user.id,
        to_user_id=offer.executor_id,
        message_type=MessageType.OFFER_ACCEPTED,
        title=f"Предложение одобрено: '{order.title}'",
        content=content,
        offer_id=offer.id,
        order_id=order.id
    )
    db.add(message_obj)
    db.commit()
    db.refresh(message_obj)
    
    return offer


@router.post("/{offer_id}/reject", response_model=OfferResponse)
def reject_offer(
    offer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Отклонение предложения заказчиком"""
    offer = crud_offer.offer.get(db, id=offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found"
        )
    
    order = crud_order.order.get(db, id=offer.order_id)
    if order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only order owner can reject offers"
        )
    
    from app.models.offer import OfferStatus
    offer_in = OfferUpdate(status=OfferStatus.rejected)
    offer = crud_offer.offer.update(db, db_obj=offer, obj_in=offer_in)
    
    # Создаем сообщение исполнителю об отклонении
    content = f"""❌ Заказчик {current_user.name} отказал в вашем предложении на проект '{order.title}'

━━━━━━━━━━━━━━━━━━━━━━
Вы можете предложить свои услуги по другому проекту или обсудить детали с заказчиком."""
    
    # Создаем сообщение напрямую через модель
    from app.models.message import Message
    message_obj = Message(
        from_user_id=current_user.id,
        to_user_id=offer.executor_id,
        message_type=MessageType.OFFER_REJECTED,
        title=f"Предложение отклонено: '{order.title}'",
        content=content,
        offer_id=offer.id,
        order_id=order.id
    )
    db.add(message_obj)
    db.commit()
    db.refresh(message_obj)
    
    return offer


@router.post("/{offer_id}/accept-by-executor", response_model=dict)
def accept_offer_by_executor(
    offer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Принятие одобренного предложения исполнителем (создание активного заказа)"""
    from app.models.offer import OfferStatus
    from sqlalchemy.orm import joinedload
    
    offer = crud_offer.offer.get(db, id=offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found"
        )
    
    # Проверяем, что офер одобрен
    if offer.status != OfferStatus.accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offer must be accepted by customer first"
        )
    
    # Проверяем, что текущий пользователь - исполнитель офера
    if offer.executor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only offer executor can accept it"
        )
    
    # Загружаем заказ с заказчиком
    from app.models.order import Order
    order = db.query(Order).options(joinedload(Order.customer)).filter(Order.id == offer.order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Меняем статус заказа на "в работе"
    # Для совместимости с реальной БД определяем корректное значение enum динамически.
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError
    try:
        conn = db.connection()
        # Получаем все значения enum orderstatus
        rows = conn.execute(
            text(
                "SELECT e.enumlabel "
                "FROM pg_type t "
                "JOIN pg_enum e ON t.oid = e.enumtypid "
                "WHERE t.typname = 'orderstatus'"
            )
        ).fetchall()
        labels = {r[0] for r in rows}
        # Ищем подходящую метку для статуса "в работе"
        if "in_progress" in labels:
            in_progress_label = "in_progress"
        elif "IN_PROGRESS" in labels:
            in_progress_label = "IN_PROGRESS"
        else:
            # Если такого статуса нет вообще, пытаемся добавить lowercase-вариант
            conn.execute(text("ALTER TYPE orderstatus ADD VALUE 'in_progress';"))
            in_progress_label = "in_progress"
        order.status = in_progress_label
        db.commit()
        db.refresh(order)
        print(f"✅ Статус заказа успешно изменен на: {order.status}")
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating order status to in_progress: {str(e)}"
        )
    
    # Если заказ уже в работе, не дублируем принятие
    current_status = str(getattr(order.status, "value", order.status)).lower()
    if current_status in ("in_progress", "in progress", "inprogress"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already in progress",
        )

    # Создаем уведомление о старте работы (нейтральное текстовое системное сообщение)
    payment_type_text = "По этапам" if offer.payment_type.value == "stages" else "Сразу после завершения"
    
    system_content = f"""🚀 Заказ '{order.title}' начат.

━━━━━━━━━━━━━━━━━━━━━━
Заказчик: {order.customer.name if order.customer else 'Заказчик'}
Исполнитель: {current_user.name}
💰 Сумма: {float(offer.total_price):,.0f} ₽
📊 Оплата: {payment_type_text}"""
    
    try:
        insert_sql = text("""
            INSERT INTO messages (from_user_id, to_user_id, offer_id, order_id, message_type, title, content, is_read)
            VALUES (:from_user_id, :to_user_id, :offer_id, :order_id, :message_type, :title, :content, FALSE)
        """)
        
        # Сообщение заказчику (от исполнителя)
        db.execute(insert_sql, {
            "from_user_id": current_user.id,
            "to_user_id": order.customer_id,
            "offer_id": offer.id,
            "order_id": order.id,
            "message_type": "text",
            "title": f"Заказ '{order.title}' начат",
            "content": system_content,
        })
        
        # Сообщение исполнителю (от заказчика)
        db.execute(insert_sql, {
            "from_user_id": order.customer_id,
            "to_user_id": current_user.id,
            "offer_id": offer.id,
            "order_id": order.id,
            "message_type": "text",
            "title": f"Заказ '{order.title}' начат",
            "content": system_content,
        })
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating notification messages: {str(e)}",
        )
    
    # Статус может быть как Enum, так и строкой — нормализуем к строке
    status_value = getattr(order.status, "value", order.status)
    return {
        "message": "Order accepted and started",
        "order_id": order.id,
        "status": status_value
    }


@router.post("/{offer_id}/reject-by-executor", response_model=OfferResponse)
def reject_offer_by_executor(
    offer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request_data: Optional[dict] = Body(None)
):
    """Отказ исполнителя от принятия заказа после одобрения заказчиком"""
    from app.models.offer import OfferStatus
    from sqlalchemy.orm import joinedload
    
    offer = crud_offer.offer.get(db, id=offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found"
        )
    
    # Проверяем, что офер одобрен
    if offer.status != OfferStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offer must be accepted by customer first"
        )
    
    # Проверяем, что текущий пользователь - исполнитель офера
    if offer.executor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only offer executor can reject it"
        )
    
    # Загружаем заказ с заказчиком
    from app.models.order import Order
    order = db.query(Order).options(joinedload(Order.customer)).filter(Order.id == offer.order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Меняем статус оффера на withdrawn (отозван)
    offer.status = OfferStatus.withdrawn
    db.add(offer)
    db.commit()
    db.refresh(offer)
    
    # Извлекаем reason из request_data если он есть
    reason = request_data.get('reason') if request_data and isinstance(request_data, dict) else None
    
    # Создаем сообщение заказчику об отказе
    reason_text = f"\n\nПричина: {reason}" if reason else ""
    content = f"""⚠️ Исполнитель {current_user.name} отказался от принятия заказа '{order.title}'

━━━━━━━━━━━━━━━━━━━━━━{reason_text}

Вы можете выбрать другого исполнителя или обсудить условия."""
    
    # Создаем сообщение напрямую через модель
    from app.models.message import Message
    message_obj = Message(
        from_user_id=current_user.id,
        to_user_id=order.customer_id,
        message_type=MessageType.OFFER_WITHDRAWN,
        title=f"Исполнитель отказался от заказа: '{order.title}'",
        content=content,
        offer_id=offer.id,
        order_id=order.id
    )
    db.add(message_obj)
    db.commit()
    db.refresh(message_obj)
    
    return offer
