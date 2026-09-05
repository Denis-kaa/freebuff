from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, aliased
from sqlalchemy import and_, or_
from app.crud.base import CRUDBase
from app.models.order import Order, OrderFile, OrderSkill, OrderStatus
from app.models.user import UserRole
from app.schemas.order import OrderCreate, OrderUpdate
from decimal import Decimal


class CRUDOrder(CRUDBase[Order, OrderCreate, OrderUpdate]):
    def create_with_skills(
        self,
        db: Session,
        *,
        obj_in: OrderCreate,
        customer_id: int
    ) -> Order:
        # Создаем заказ
        order_data = obj_in.model_dump(exclude={"skills"})
        order_data["customer_id"] = customer_id
        db_obj = Order(**order_data)
        db.add(db_obj)
        db.flush()

        # Добавляем навыки
        if obj_in.skills:
            for skill_name in obj_in.skills:
                skill = OrderSkill(order_id=db_obj.id, skill_name=skill_name)
                db.add(skill)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_multi_with_filters(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        category_id: Optional[str] = None,
        subcategory_id: Optional[str] = None,
        subsubcategory_id: Optional[str] = None,
        # Массивы ID для фильтрации по всей иерархии
        category_ids: Optional[List[str]] = None,
        subcategory_ids: Optional[List[str]] = None,
        subsubcategory_ids: Optional[List[str]] = None,
        budget_from: Optional[Decimal] = None,
        budget_to: Optional[Decimal] = None,
        keywords: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        customer_id: Optional[int] = None,
        # Новые фильтры
        min_hired_percent: Optional[float] = None,
        offers_count_from: Optional[int] = None,
        offers_count_to: Optional[int] = None,
    ) -> tuple[List[Order], int]:
        from sqlalchemy import func
        from app.models.offer import Offer

        query = db.query(Order)

        # Фильтры по категории (одиночные — для обратной совместимости)
        if category_id:
            query = query.filter(Order.category_id == category_id)
        if subcategory_id:
            query = query.filter(Order.subcategory_id == subcategory_id)
        if subsubcategory_id:
            query = query.filter(Order.subsubcategory_id == subsubcategory_id)

        # Фильтры по категории (массивы — фильтрация по всей иерархии)
        if category_ids:
            query = query.filter(Order.category_id.in_(category_ids))
        if subcategory_ids:
            if subsubcategory_ids:
                query = query.filter(or_(
                    Order.subcategory_id.in_(subcategory_ids),
                    Order.subsubcategory_id.in_(subsubcategory_ids)
                ))
            else:
                query = query.filter(Order.subcategory_id.in_(subcategory_ids))
        if subsubcategory_ids and not subcategory_ids:
            query = query.filter(Order.subsubcategory_id.in_(subsubcategory_ids))

        # Фильтры по бюджету
        # budget_from: показываем заказы где budget_to >= запрошенного минимума
        # Или budget_to = NULL (заказчик не указал верхнюю границу) - тогда ещё ориентируемся по budget_from
        if budget_from:
            query = query.filter(
                or_(
                    Order.budget_to >= budget_from,
                    and_(Order.budget_to == None, Order.budget_from >= budget_from)
                )
            )
        # budget_to: показываем заказы где budget_from <= запрошенного максимума
        # Или budget_from = NULL (не указана нижняя граница) - тогда ещё ориентируемся по budget_to
        if budget_to:
            query = query.filter(
                or_(
                    Order.budget_from <= budget_to,
                    and_(Order.budget_from == None, Order.budget_to <= budget_to)
                )
            )

        # Поиск по ключевому слову
        if keywords:
            from app.models.category import Category
            cat_alias = aliased(Category)
            subcat_alias = aliased(Category)
            subsubcat_alias = aliased(Category)
            
            search = f"%{keywords}%"
            query = query.outerjoin(cat_alias, Order.category_id == cat_alias.id)
            query = query.outerjoin(subcat_alias, Order.subcategory_id == subcat_alias.id)
            query = query.outerjoin(subsubcat_alias, Order.subsubcategory_id == subsubcat_alias.id)
            
            query = query.filter(
                or_(
                    Order.title.ilike(search),
                    Order.description.ilike(search),
                    cat_alias.name.ilike(search),
                    subcat_alias.name.ilike(search),
                    subsubcat_alias.name.ilike(search)
                )
            )

        # Фильтр по статусу
        if status:
            query = query.filter(Order.status == status)
        elif customer_id is None:
            # Публичный список — только OPEN заказы
            # Публичный список — только OPEN заказы
            query = query.filter(Order.status == OrderStatus.open)

        if customer_id:
            query = query.filter(Order.customer_id == customer_id)

        # Фильтр по количеству откликов (offers_count)
        if offers_count_from is not None or offers_count_to is not None:
            offers_subq = (
                db.query(Offer.order_id, func.count(Offer.id).label("cnt"))
                .group_by(Offer.order_id)
                .subquery()
            )
            query = query.outerjoin(offers_subq, Order.id == offers_subq.c.order_id)
            if offers_count_from is not None:
                query = query.filter(
                    func.coalesce(offers_subq.c.cnt, 0) >= offers_count_from
                )
            if offers_count_to is not None:
                query = query.filter(
                    func.coalesce(offers_subq.c.cnt, 0) <= offers_count_to
                )

        # Фильтр по проценту найма заказчика (min_hired_percent)
        # Показываем заказы, у которых заказчик нанял >= min_hired_percent % исполнителей
        if min_hired_percent is not None and min_hired_percent > 0:
            total_sub = (
                db.query(
                    Order.customer_id,
                    func.count(Order.id).label("total")
                )
                .group_by(Order.customer_id)
                .subquery()
            )
            completed_sub = (
                db.query(
                    Order.customer_id,
                    func.count(Order.id).label("completed")
                )
                .filter(Order.status == OrderStatus.completed)
                .group_by(Order.customer_id)
                .subquery()
            )
            query = (
                query
                .join(total_sub, Order.customer_id == total_sub.c.customer_id)
                .outerjoin(completed_sub, Order.customer_id == completed_sub.c.customer_id)
                .filter(
                    (func.coalesce(completed_sub.c.completed, 0) * 100.0 / total_sub.c.total)
                    >= min_hired_percent
                )
            )

        total = query.count()
        items = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    def update_with_skills(
        self,
        db: Session,
        *,
        db_obj: Order,
        obj_in: OrderUpdate
    ) -> Order:
        # Обновляем заказ
        update_data = obj_in.model_dump(exclude_unset=True, exclude={"skills"})
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # Обновляем навыки если они переданы
        if obj_in.skills is not None:
            # Удаляем старые навыки
            db.query(OrderSkill).filter(OrderSkill.order_id == db_obj.id).delete()
            # Добавляем новые
            for skill_name in obj_in.skills:
                skill = OrderSkill(order_id=db_obj.id, skill_name=skill_name)
                db.add(skill)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


class CRUDOrderFile(CRUDBase[OrderFile, Dict[str, Any], Dict[str, Any]]):
    def create_for_order(
        self,
        db: Session,
        *,
        order_id: int,
        file_path: str,
        file_name: str,
        file_size: Optional[int] = None,
        file_type: Optional[str] = None
    ) -> OrderFile:
        db_obj = OrderFile(
            order_id=order_id,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            file_type=file_type
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_order_id(self, db: Session, *, order_id: int):
        return db.query(OrderFile).filter(OrderFile.order_id == order_id).all()


order = CRUDOrder(Order)
order_file = CRUDOrderFile(OrderFile)
