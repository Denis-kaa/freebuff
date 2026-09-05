from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.websocket_manager import manager
from app.core.security import verify_token
from app.models.user import User
from jose import JWTError
import json

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint для real-time сообщений"""
    # Принимаем подключение СРАЗУ, до любых проверок
    # Это необходимо, так как FastAPI может отклонять подключение до выполнения кода
    try:
        await websocket.accept()
        print(f"✅ WebSocket connection accepted from {websocket.client}")
        print(f"WebSocket query_params: {websocket.query_params}")
        print(f"WebSocket headers: {dict(websocket.headers)}")
    except Exception as e:
        print(f"❌ Error accepting WebSocket: {e}")
        return
    
    db = None
    try:
        # Получаем токен из query параметров или заголовков
        token = None
        # Пробуем получить из query параметров
        if "token" in websocket.query_params:
            token = websocket.query_params.get("token")
            print(f"Token found in query params")
        # Если нет в query, пробуем из заголовков
        elif "authorization" in websocket.headers:
            auth_header = websocket.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                print(f"Token found in headers")
        
        if not token:
            print("❌ WebSocket: No token provided")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="No token provided")
            return
        
        # Проверяем токен
        payload = verify_token(token)
        if payload is None:
            print(f"❌ WebSocket: Invalid token - verify_token returned None")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return
        
        # Получаем email из токена и находим пользователя
        email: str = payload.get("sub")
        if email is None:
            print(f"❌ WebSocket: No email in token payload")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="No email in token")
            return
        
        # Получаем user_id из базы данных
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            if user is None:
                print(f"❌ WebSocket: User not found for email: {email}")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
                return
            
            user_id = user.id
            print(f"✅ WebSocket: User authenticated - user_id={user_id}, email={email}")
            
            # Подключаем пользователя к менеджеру
            await manager.connect(websocket, user_id)
            print(f"✅ WebSocket: User {user_id} connected successfully")
            
            try:
                while True:
                    # Ждем сообщения от клиента (можно использовать для heartbeat)
                    data = await websocket.receive_text()
                    # Можно обрабатывать входящие сообщения, если нужно
                    # Отправляем pong для поддержания соединения
                    try:
                        await websocket.send_text(json.dumps({"type": "pong"}))
                    except:
                        pass
            except WebSocketDisconnect:
                print(f"🔌 WebSocket: User {user_id} disconnected")
                manager.disconnect(websocket, user_id)
        finally:
            if db:
                db.close()
    except JWTError as e:
        print(f"❌ WebSocket: JWTError - {e}")
        import traceback
        traceback.print_exc()
        if db:
            db.close()
        try:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="JWT Error")
        except:
            pass
    except Exception as e:
        print(f"❌ WebSocket: Unexpected error - {e}")
        import traceback
        traceback.print_exc()
        if db:
            db.close()
        try:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Server error")
        except:
            pass
