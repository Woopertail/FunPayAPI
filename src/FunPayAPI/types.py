"""
В данном модуле описаны все типы пакета FunPayAPI.
"""

from enum import Enum
import time


class Links:
    """
    Основные ссылки для работы с FunPay API.
    """
    BASE_URL = "https://funpay.com"
    ORDERS = "https://funpay.com/orders/trade"
    USER = "https://funpay.com/users"
    RAISE = "https://funpay.com/lots/raise"
    RUNNER = "https://funpay.com/runner/"
    REFUND = "https://funpay.com/orders/refund"


class EventTypes(Enum):
    """
    Типы событий.

    EventTypes.INITIAL_MESSAGE - обнаружено новое сообщение (при первом запросе Runner'а).

    EventTypes.MESSAGES_LIST_CHANGED - список чатов и/или содержимое одного/нескольких чатов изменилось.

    EventTypes.NEW_MESSAGE - в чате обнаружено новое сообщение.

    EventTypes.INITIAL_ORDER - обнаружен новый заказ (при первом запросе Runner'а).

    EventTypes.ORDERS_LIST_CHANGED - список заказов и/или статус одного/нескольких заказов изменился.

    EventTypes.NEW_ORDER - в списке заказов обнаружен новый заказ.

    EventTypes.ORDER_STATUS_CHANGED - статус заказа изменился.
    """
    INITIAL_MESSAGE = 0
    MESSAGES_LIST_CHANGED = 1
    NEW_MESSAGE = 2
    INITIAL_ORDER = 3
    ORDERS_LIST_CHANGED = 4
    NEW_ORDER = 5
    ORDER_STATUS_CHANGED = 6


class CategoryTypes(Enum):
    """
    Типы категорий FunPay.

    CategoryTypes.LOT - стандартный лот.

    CategoryTypes.CURRENCY - лот с игровой валютой (их нельзя поднимать).
    """
    LOT = 0
    CURRENCY = 1


class OrderStatuses(Enum):
    """
    Состояния ордеров.

    OrderStatuses.OUTSTANDING - ожидает выполнения.

    OrderStatuses.COMPLETED - выполнен.

    OrderStatuses.REFUND - запрошен возврат средств.
    """
    OUTSTANDING = 0
    COMPLETED = 1
    REFUND = 2


class Order:
    """
    Класс, хранящий информацию о заказе.
    """
    def __init__(self, html: str,
                 id_: str,
                 title: str,
                 price: float,
                 buyer_username: str,
                 buyer_id: int,
                 status: OrderStatuses):
        """
        :param html: HTML код заказа.

        :param id_: ID заказа.

        :param title: Краткое описание заказа.

        :param price: Оплаченная сумма за заказ.

        :param buyer_username: Никнейм покупателя.

        :param buyer_id: ID покупателя.

        :param status: статус заказа.
        """
        self.html = html
        self.id = id_
        self.title = title
        self.price = price
        self.buyer_username = buyer_username
        self.buyer_id = buyer_id
        self.status = status


class Message:
    """
    Класс, хранящий информацию о сообщении.
    """
    def __init__(self, text: str, node_id: int, chat_with: str | None, unread: bool = False):
        """
        :param text: текст сообщения.

        :param node_id: ID чата.

        :param chat_with: никнейм пользователя, из чата с которым получено сообщение.

        :param unread: установлен ли флаг "unread" у чата, в котором получено сообщение (на момент получения сообщения)
        """
        self.node_id = node_id
        self.text = text
        self.chat_with = chat_with
        self.unread = unread


class Lot:
    """
    Класс, описывающий лот.
    """
    def __init__(self,
                 category_id: int,
                 game_id: int | None,
                 id_: int,
                 title: str,
                 price: str):
        """
        :param category_id: ID категории, к которой относится лот.

        :param game_id: ID игры, к которой относится лот.

        :param id_: ID лота.

        :param title: название лота.

        :param price: цена лота.
        """
        # todo: добавить html-код лота.
        self.category_id = category_id
        self.game_id = game_id
        self.id = id_
        self.title = title
        self.price = price


class Category:
    """
    Класс, описывающий категорию.
    """
    def __init__(self, id_: int, game_id: int | None, title: str, edit_lots_link: str, public_link: str,
                 type_: CategoryTypes):
        """
        :param id_: ID категории.

        :param game_id: ID игры, к которой относится категория.

        :param title: название категории.

        :param edit_lots_link: ссылка на страницу редактирования лотов данной категории.

        :param public_link: ссылка на все лоты всех пользователей в данной категории.

        :param type_: тип категории.
        """
        self.id = id_
        self.game_id = game_id
        self.title = title
        self.edit_lots_link = edit_lots_link
        self.public_link = public_link
        self.type = type_


class Event:
    """
    Базовый класс события.
    """
    def __init__(self, event_type: EventTypes, event_time: int, tag: str | None):
        """
        :param event_type: тип события.

        :param event_time: время события.

        :param tag: тег runner'а.
        """
        self.type = event_type
        self.time = event_time
        self.tag = tag


class InitialMessageEvent(Event):
    """
    Класс события: обнаружено новое сообщение (при первом запросе Runner'а).
    """
    def __init__(self, message_obj: Message, tag: str):
        """
        :param message_obj: экземпляр класса, описывающий сообщение.

        :param tag: тег runner'а.
        """
        super(InitialMessageEvent, self).__init__(EventTypes.INITIAL_MESSAGE, int(time.time()), tag)
        self.message = message_obj


class MessagesListChangedEvent(Event):
    """
    Класс события: список чатов и/или содержимое одного/нескольких чатов изменилось.
    """
    def __init__(self, tag: str):
        """
        :param tag: тэг runner'а.
        """
        super(MessagesListChangedEvent, self).__init__(EventTypes.MESSAGES_LIST_CHANGED, int(time.time()), tag)


class NewMessageEvent(Event):
    """
    Класс события: в чате обнаружено новое сообщение.
    """
    def __init__(self, message_obj: Message, tag: str | None):
        """
        :param message_obj: экземпляр класса, описывающий сообщение.

        :param tag: тег runner'а.
        """
        super(NewMessageEvent, self).__init__(EventTypes.NEW_MESSAGE, int(time.time()), tag)
        self.message = message_obj


class InitialOrderEvent(Event):
    """
    Класс события: обнаружен новый заказ (при первом запросе Runner'а).
    """
    def __init__(self, order_obj: Order, tag: str):
        """
        :param order_obj: экземпляр класса, описывающий заказ.

        :param tag: тег runner'а.
        """
        super(InitialOrderEvent, self).__init__(EventTypes.INITIAL_ORDER, int(time.time()), tag)
        self.order = order_obj


class OrdersListChangedEvent(Event):
    """
    Класс события: список заказов и/или статус одного/нескольких заказов изменился.
    """
    def __init__(self, buyer: int, seller: int, tag: str):
        """
        :param buyer: кол-во активных покупок.

        :param seller: кол-во активных продаж.

        :param tag: тэг runner'а.
        """
        super(OrdersListChangedEvent, self).__init__(EventTypes.ORDERS_LIST_CHANGED, int(time.time()), tag)
        self.buyer = buyer
        self.seller = seller


class NewOrderEvent(Event):
    """
    Класс события: в списке заказов обнаружен новый заказ.
    """
    def __init__(self, order_obj: Order, tag: str | None):
        """
        :param order_obj: экземпляр класса, описывающий заказ.

        :param tag: тег runner'а.
        """
        super(NewOrderEvent, self).__init__(EventTypes.NEW_ORDER, int(time.time()), tag)
        self.order = order_obj


class OrderStatusChangedEvent(Event):
    """
    Класс события: статус заказа изменился.
    """
    def __init__(self, order_obj: Order, tag: str | None):
        """
        :param order_obj: экземпляр класса, описывающий заказ.

        :param tag: тег runner'а.
        """
        super(OrderStatusChangedEvent, self).__init__(EventTypes.ORDER_STATUS_CHANGED, int(time.time()), tag)
        self.order = order_obj


class RaiseResponse:
    """
    Класс, описывающий ответ FunPay на запрос о поднятии лотов.
    """
    def __init__(self, complete: bool, wait: int, raised_category_names: list[str], funpay_response: dict):
        """
        :param complete: удалось ли поднять лоты.

        :param wait: примерное время ожидания до следующего поднятия.

        :param raised_category_names: названия поднятых категорий (из modal-формы).

        :param funpay_response: полный ответ Funpay.
        """
        self.complete = complete
        self.wait = wait
        self.raised_category_names = raised_category_names
        self.funpay_response = funpay_response


class UserInfo:
    """
    Класс, хранящий информацию о лотах и категориях пользователя.
    """
    def __init__(self, lots: list[Lot], categories: list[Category]):
        """
        :param lots: список лотов пользователя.

        :param categories: список категорий пользователя.
        """
        self.lots = lots
        self.categories = categories
