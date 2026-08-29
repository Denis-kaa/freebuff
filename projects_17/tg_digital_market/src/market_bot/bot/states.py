"""FSM-состояния aiogram.

Используются только в aiogram-обработчиках; core-слой про них не знает.
В MVP только seller-флоу требует FSM (ввод товара). Cart-флоу реализован
через inline-кнопки (без FSM) для простоты.
"""

from aiogram.fsm.state import State, StatesGroup


class CatalogBrowsing(StatesGroup):
    listing_categories = State()
    listing_products = State()
    viewing_product = State()


class SellerFlow(StatesGroup):
    adding_name = State()
    adding_description = State()
    adding_category = State()
    adding_price = State()
    adding_keys = State()
