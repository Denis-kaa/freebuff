"""services/catalog.py — операции каталога для UI.

Тонкий сервис поверх Repository: фильтры, сортировка, bulk-ключи.
Не хранит своего состояния.
"""

from __future__ import annotations

from typing import Iterable, Optional

from ..db.repository import Repository
from ..models import Product


class CatalogService:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def list_active(self, category: Optional[str] = None) -> list[Product]:
        return self._repo.list_products(active_only=True, category=category)

    def list_categories(self) -> list[str]:
        return self._repo.list_distinct_categories()

    def get(self, product_id: int) -> Optional[Product]:
        return self._repo.get_product(product_id)

    def available_stock(self, product_id: int) -> int:
        return self._repo.count_available_keys(product_id)

    def search(self, query: str, category: Optional[str] = None) -> list[Product]:
        """Поиск по подстроке в имени/описании (регистронезависимо)."""
        needle = f"%{query.lower()}%"
        # SQL — Repository это не делает; добавим узкую функцию-фильтр.
        products = self._repo.list_products(active_only=True, category=category)
        q = query.lower()
        return [
            p
            for p in products
            if q in p.name.lower() or q in p.description.lower()
        ]

    def bulk_add_keys(self, product_id: int, codes: Iterable[str]) -> int:
        return self._repo.add_keys(product_id, codes)

    # ── seller/CRUD ─────────────────────────────────────────────────────────

    def seller_create(
        self,
        seller_id: int,
        name: str,
        description: str,
        category: str,
        price_stars: int,
    ) -> Product:
        if price_stars < 1:
            raise ValueError("Цена должна быть >= 1 звезды.")
        if not name.strip():
            raise ValueError("Название товара не может быть пустым.")
        return self._repo.create_product(
            seller_id=seller_id,
            name=name.strip(),
            description=description.strip(),
            category=category.strip().lower() or "other",
            price_stars=price_stars,
        )

    def seller_update(
        self,
        product_id: int,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        price_stars: Optional[int] = None,
    ) -> Optional[Product]:
        return self._repo.update_product(
            product_id,
            name=name.strip() if name is not None else None,
            description=description.strip() if description is not None else None,
            category=category.strip().lower() if category is not None else None,
            price_stars=price_stars,
        )

    def set_active(self, product_id: int, is_active: bool) -> None:
        self._repo.set_product_active(product_id, is_active)
