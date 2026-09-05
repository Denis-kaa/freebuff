from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.category import Category


class CRUDCategory(CRUDBase[Category, Dict[str, Any], Dict[str, Any]]):
    def get_tree(self, db: Session) -> List[Dict[str, Any]]:
        """Возвращает полное дерево категорий (root → children → children)"""
        roots = db.query(Category).filter(Category.parent_id.is_(None)).all()
        return [self._build_tree_node(root) for root in roots]

    def _build_tree_node(self, category: Category) -> Dict[str, Any]:
        node = {
            "id": category.id,
            "name": category.name,
            "parent_id": category.parent_id,
        }
        if category.children:
            node["subcategories"] = [
                self._build_tree_node(child) for child in category.children
            ]
        return node

    def get_by_parent_id(self, db: Session, *, parent_id: Optional[str] = None) -> List[Category]:
        """Получить категории по parent_id (None = корневые)"""
        if parent_id is None:
            return db.query(Category).filter(Category.parent_id.is_(None)).all()
        return db.query(Category).filter(Category.parent_id == parent_id).all()

    def create_many(self, db: Session, *, categories: List[Dict[str, Any]]) -> int:
        """Массовое создание категорий. Возвращает количество созданных."""
        existing_ids = {c.id for c in db.query(Category.id).all()}
        created = 0
        for cat_data in categories:
            if cat_data["id"] not in existing_ids:
                db.add(Category(**cat_data))
                created += 1
        db.commit()
        return created


category = CRUDCategory(Category)
