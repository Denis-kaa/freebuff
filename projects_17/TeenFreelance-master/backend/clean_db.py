import sys
import os

# Добавляем текущую директорию в sys.path для корректных импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models import (
    User, UserProfile, UserSkill, Order, OrderFile, OrderSkill,
    Offer, OfferStage, PortfolioItem, PortfolioFile,
    Post, PostImage, Comment, PostLike, OrderNote, Message
)

def clean_db():
    db = SessionLocal()
    try:
        print("Начинаем очистку базы данных...")
        
        # Удаляем записи в порядке, учитывающем внешние ключи
        # (сначала зависимые таблицы, потом основные)
        
        print("Удаляем сообщения и заметки...")
        db.query(Message).delete()
        db.query(OrderNote).delete()
        
        print("Удаляем данные сообщества (лайки, комментарии, посты)...")
        db.query(PostLike).delete()
        db.query(Comment).delete()
        db.query(PostImage).delete()
        db.query(Post).delete()
        
        print("Удаляем портфолио...")
        db.query(PortfolioFile).delete()
        db.query(PortfolioItem).delete()
        
        print("Удаляем офферы и этапы...")
        db.query(OfferStage).delete()
        db.query(Offer).delete()
        
        print("Удаляем заказы и файлы заказов...")
        db.query(OrderSkill).delete()
        db.query(OrderFile).delete()
        db.query(Order).delete()
        
        print("Удаляем профили, навыки и пользователей...")
        db.query(UserSkill).delete()
        db.query(UserProfile).delete()
        db.query(User).delete()
        
        db.commit()
        print("✅ База данных успешно очищена!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при очистке базы данных: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    clean_db()
