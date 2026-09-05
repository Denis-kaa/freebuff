from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.message import Message, MessageType
from app.crud import message as crud_message
from app.schemas.message import MessageResponse, MessageWithUsers, MessageCreate
from app.websocket_manager import manager

router = APIRouter()


@router.get("", response_model=List[MessageWithUsers])
def get_messages(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Получение всех сообщений текущего пользователя (для списка диалогов). Без жесткого лимита."""
    from sqlalchemy import text
    from sqlalchemy.orm import joinedload
    from app.models.offer import Offer
    from app.models.order import Order
    
    # Отдаем все сообщения пользователя по возрастанию времени
    query = text("""
        SELECT m.*, 
               u1.name as from_user_name,
               u2.name as to_user_name
        FROM messages m
        LEFT JOIN users u1 ON m.from_user_id = u1.id
        LEFT JOIN users u2 ON m.to_user_id = u2.id
        WHERE m.from_user_id = :user_id OR m.to_user_id = :user_id
        ORDER BY m.created_at ASC
    """)
    
    rows = db.execute(query, {
        "user_id": current_user.id,
    }).fetchall()
    
    result = []
    for row in rows:
        # Преобразуем message_type в нижний регистр, так как из БД может прийти в верхнем
        message_type = str(row.message_type).lower()
        
        msg_dict = {
            "id": row.id,
            "from_user_id": row.from_user_id,
            "to_user_id": row.to_user_id,
            "message_type": message_type,
            "title": row.title,
            "content": row.content,
            "offer_id": row.offer_id,
            "order_id": row.order_id,
            "is_read": row.is_read,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "from_user_name": row.from_user_name or "",
            "to_user_name": row.to_user_name or "",
        }
        
        # Добавляем данные оффера если есть
        if row.offer_id:
            offer = db.query(Offer).options(
                joinedload(Offer.stages)
            ).filter(Offer.id == row.offer_id).first()
            if offer:
                msg_dict["offer_data"] = {
                    "id": offer.id,
                    "description": offer.description,
                    "total_price": float(offer.total_price),
                    "payment_type": offer.payment_type.value,
                    "deadline": offer.deadline.isoformat() if offer.deadline else None,
                    "status": offer.status.value,
                    "stages": [
                        {
                            "name": stage.name,
                            "price": float(stage.price),
                            "order_num": stage.order_num
                        }
                        for stage in offer.stages
                    ] if offer.stages else []
                }
        
        # Добавляем данные заказа если есть
        if row.order_id:
            order = db.query(Order).filter(Order.id == row.order_id).first()
            if order:
                msg_dict["order_data"] = {
                    "id": order.id,
                    "title": order.title,
                    "description": order.description,
                    "status": order.status.value
                }
        
        result.append(msg_dict)
    
    return result


@router.get("/unread-count", response_model=dict)
def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Получение количества непрочитанных сообщений"""
    count = crud_message.message.get_unread_count(db, user_id=current_user.id)
    return {"count": count}


@router.post("/{message_id}/read", response_model=MessageResponse)
def mark_as_read(
    message_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Отметить сообщение как прочитанное"""
    message = crud_message.message.mark_as_read(
        db, message_id=message_id, user_id=current_user.id
    )
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    return message


@router.get("/conversation/{user_id}", response_model=List[MessageWithUsers])
def get_conversation(
    user_id: int,
    # Сколько сообщений за раз отдаем (как в мессенджерах)
    limit: int = 100,
    # Для подгрузки истории: брать сообщения «старше», чем этот id
    before_id: int | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Получение переписки с конкретным пользователем.
    - Безлимитная история: можно подгружать порциями по limit.
    - По умолчанию отдает последние limit сообщений.
    - Для подгрузки старых сообщений передаем before_id (id самого старого сообщения, которое уже есть на клиенте).
    """
    from sqlalchemy import text
    from sqlalchemy.orm import joinedload
    from app.models.offer import Offer
    from app.models.order import Order
    
    # Базовый SQL: берем сообщения только между двумя пользователями
    base_sql = """
        SELECT m.*, 
               u1.name as from_user_name,
               u2.name as to_user_name
        FROM messages m
        LEFT JOIN users u1 ON m.from_user_id = u1.id
        LEFT JOIN users u2 ON m.to_user_id = u2.id
        WHERE (m.from_user_id = :current_user_id AND m.to_user_id = :user_id)
           OR (m.from_user_id = :user_id AND m.to_user_id = :current_user_id)
    """
    
    params: dict = {
        "current_user_id": current_user.id,
        "user_id": user_id,
        "limit": limit,
    }
    
    # Если передали before_id — подгружаем сообщения старше этого id
    if before_id is not None:
        base_sql += " AND m.id < :before_id"
        params["before_id"] = before_id
    
    # Отдаем последние limit сообщений (по id), а потом разворачиваем их по времени по возрастанию
    base_sql += " ORDER BY m.id DESC LIMIT :limit"
    query = text(base_sql)
    
    rows_desc = db.execute(query, params).fetchall()
    rows = list(reversed(rows_desc))
    
    result = []
    for row in rows:
        # Преобразуем message_type в нижний регистр
        message_type = str(row.message_type).lower()
        
        msg_dict = {
            "id": row.id,
            "from_user_id": row.from_user_id,
            "to_user_id": row.to_user_id,
            "message_type": message_type,
            "title": row.title,
            "content": row.content,
            "offer_id": row.offer_id,
            "order_id": row.order_id,
            "is_read": row.is_read,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "from_user_name": row.from_user_name or "",
            "to_user_name": row.to_user_name or "",
        }
        
        # Добавляем данные оффера если есть
        if row.offer_id:
            offer = db.query(Offer).options(
                joinedload(Offer.stages)
            ).filter(Offer.id == row.offer_id).first()
            if offer:
                msg_dict["offer_data"] = {
                    "id": offer.id,
                    "description": offer.description,
                    "total_price": float(offer.total_price),
                    "payment_type": offer.payment_type.value,
                    "deadline": offer.deadline.isoformat() if offer.deadline else None,
                    "status": offer.status.value,
                }
        
        # Добавляем данные заказа если есть
        if row.order_id:
            order = db.query(Order).filter(Order.id == row.order_id).first()
            if order:
                msg_dict["order_data"] = {
                    "id": order.id,
                    "title": order.title,
                    "description": order.description,
                    "status": order.status.value
                }
        
        result.append(msg_dict)
    
    return result


@router.post("", response_model=MessageWithUsers)
async def create_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Создание нового сообщения"""
    from sqlalchemy import text
    from sqlalchemy.orm import joinedload
    from app.models.offer import Offer
    from app.models.order import Order
    
    # Создаем сообщение напрямую, так как from_user_id берется из current_user
    # Преобразуем message_type в правильный enum
    if isinstance(message_data.message_type, str):
        if message_data.message_type.lower() == 'text':
            message_type_enum = MessageType.text
        else:
            message_type_enum = MessageType(message_data.message_type.lower())
    else:
        message_type_enum = message_data.message_type
    
    # Получаем строковое значение enum для сохранения в базу
    # SQLAlchemy с PostgreSQL enum может использовать имя константы вместо значения
    message_type_value = message_type_enum.value if hasattr(message_type_enum, 'value') else str(message_type_enum)
    
    # Используем прямое SQL выполнение для обхода проблемы с enum
    from sqlalchemy import text
    result = db.execute(
        text("""
            INSERT INTO messages (from_user_id, to_user_id, offer_id, order_id, message_type, title, content, is_read)
            VALUES (:from_user_id, :to_user_id, :offer_id, :order_id, :message_type, :title, :content, :is_read)
            RETURNING id, created_at
        """),
        {
            "from_user_id": current_user.id,
            "to_user_id": message_data.to_user_id,
            "offer_id": message_data.offer_id,
            "order_id": message_data.order_id,
            "message_type": message_type_value,  # Используем строковое значение напрямую
            "title": message_data.title,
            "content": message_data.content,
            "is_read": False
        }
    )
    row = result.fetchone()
    message_id = row[0]
    created_at = row[1]
    db.commit()
    
    # Загружаем созданное сообщение через прямое SQL для обхода проблемы с enum
    query = text("""
        SELECT m.*, 
               u1.name as from_user_name,
               u2.name as to_user_name
        FROM messages m
        LEFT JOIN users u1 ON m.from_user_id = u1.id
        LEFT JOIN users u2 ON m.to_user_id = u2.id
        WHERE m.id = :message_id
    """)
    
    row = db.execute(query, {"message_id": message_id}).fetchone()
    
    # Преобразуем message_type в нижний регистр
    message_type_value = str(row.message_type).lower()
    
    result = {
        "id": row.id,
        "from_user_id": row.from_user_id,
        "to_user_id": row.to_user_id,
        "message_type": message_type_value,
        "title": row.title,
        "content": row.content,
        "offer_id": row.offer_id,
        "order_id": row.order_id,
        "is_read": row.is_read,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "from_user_name": row.from_user_name or "",
        "to_user_name": row.to_user_name or "",
    }
    
    # Добавляем данные оффера если есть
    if row.offer_id:
        offer = db.query(Offer).options(
            joinedload(Offer.stages)
        ).filter(Offer.id == row.offer_id).first()
        if offer:
            result["offer_data"] = {
                "id": offer.id,
                "description": offer.description,
                "total_price": float(offer.total_price),
                "payment_type": offer.payment_type.value,
                "deadline": offer.deadline.isoformat() if offer.deadline else None,
                "status": offer.status.value,
            }
    
    # Добавляем данные заказа если есть
    if row.order_id:
        order = db.query(Order).filter(Order.id == row.order_id).first()
        if order:
            result["order_data"] = {
                "id": order.id,
                "title": order.title,
                "description": order.description,
                "status": order.status.value
            }
    
    # Отправляем новое сообщение через WebSocket получателю и отправителю
    try:
        print(f"Sending message via WebSocket - to_user_id={message_data.to_user_id}, from_user_id={current_user.id}")
        # Преобразуем в JSON-совместимый формат (datetime -> isoformat и т.п.)
        ws_message = jsonable_encoder(result)
        # Получателю
        await manager.send_personal_message({
            "type": "new_message",
            "message": ws_message
        }, message_data.to_user_id)
        print(f"Message sent to user {message_data.to_user_id} via WebSocket")
        
        # Отправителю для обновления его UI
        await manager.send_personal_message({
            "type": "message_sent",
            "message": ws_message
        }, current_user.id)
        print(f"Message sent to sender {current_user.id} via WebSocket")
    except Exception as e:
        # Если WebSocket не работает, просто логируем ошибку
        print(f"WebSocket error when sending message: {e}")
        import traceback
        traceback.print_exc()
    
    return result
