from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_orderstatus_review_enum():
    """
    Гарантирует, что в enum orderstatus есть значение 'review'.
    """
    with engine.connect() as conn:
        try:
            # Проверяем, есть ли уже значение review
            result = conn.execute(
                text(
                    "SELECT e.enumlabel "
                    "FROM pg_type t "
                    "JOIN pg_enum e ON t.oid = e.enumtypid "
                    "WHERE t.typname = 'orderstatus' AND e.enumlabel = 'review'"
                )
            )
            exists = result.first() is not None
            if not exists:
                conn.execute(text("ALTER TYPE orderstatus ADD VALUE 'review';"))
        except Exception:
            # Если БД не PostgreSQL или тип другой — молча пропускаем
            pass

