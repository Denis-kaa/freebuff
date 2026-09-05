from fastapi import APIRouter

router = APIRouter()


@router.get("")
def read_categories():
    """Получение дерева категорий"""
    # Импортируем категории из frontend файла или создаем отдельный файл
    # Пока возвращаем структуру из ordersCategories.js
    # В будущем можно перенести в БД
    return {
        "message": "Categories endpoint - will return categories from ordersCategories.js structure"
    }
