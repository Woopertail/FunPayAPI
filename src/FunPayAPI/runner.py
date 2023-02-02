"""
В данном модуле написан класс Runner'а.
"""

from bs4 import BeautifulSoup
from typing import Iterator
from copy import deepcopy
import traceback
import requests
import logging
import json
import time

from . import utils
from . import types
from . import account
from . import exceptions


logger = logging.getLogger("FunPayAPI.runner")


class Runner:
    """
    Класс для получения новых событий с FunPay.
    """
    def __init__(self, account: account.Account, timeout: float | int = 10.0):
        """
        :param account: экземпляр класса аккаунта.

        :param timeout: тайм-аут ожидания ответа на запросы.
        """
        self.account = account
        self.timeout = timeout

        self.last_message_event_tag = utils.gen_random_tag()
        self.last_order_event_tag = utils.gen_random_tag()

        self.saved_messages: dict[int, types.Message] = {}
        self.saved_orders: dict[str, types.Order] = {}

        self.first_request = True

    def get_updates(self) -> list[types.NewMessageEvent | types.NewOrderEvent | types.OrderStatusChangedEvent]:
        """
        Получает и парсит список событий FunPay.

        :return: список событий.
        """
        if not self.account.is_authorized():
            raise exceptions.NotAuthorized()

        orders = {
            "type": "orders_counters",
            "id": self.account.id,
            "tag": self.last_order_event_tag,
            "data": False
        }
        chats = {
            "type": "chat_bookmarks",
            "id": self.account.id,
            "tag": self.last_message_event_tag,
            "data": False
        }
        payload = {
            "objects": json.dumps([orders, chats]),
            "request": False,
            "csrf_token": self.account.csrf_token
        }
        headers = {
            "accept": "*/*",
            "cookie": f"golden_key={self.account.golden_key}; PHPSESSID={self.account.session_id}",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "user-agent": self.account.user_agent
        }

        response = requests.post(types.Links.RUNNER, headers=headers, data=payload, timeout=self.timeout)
        logger.debug(f"Статус-код получения данных о событиях: {response.status_code}.")
        if response.status_code != 200:
            raise exceptions.StatusCodeIsNot200(response.status_code)

        json_response = response.json()
        logger.debug(f"Получены данные о событиях: {json_response}")

        events = []

        for obj in json_response["objects"]:
            if obj.get("type") == "chat_bookmarks":
                if not self.first_request:
                    events.append(types.MessagesListChangedEvent(self.last_message_event_tag))
                self.last_message_event_tag = obj.get("tag")
                self.account.update_chats(obj["data"]["html"])
                soup = BeautifulSoup(obj["data"]["html"], "html.parser")
                messages = soup.find_all("a", {"class": "contact-item"})

                for msg in messages:
                    unread = True if "unread" in msg.get("class") else False
                    node_id = int(msg["data-id"])
                    message_text = msg.find("div", {"class": "contact-item-message"}).text
                    # Если это старое сообщение (сохранено в self.last_messages) -> пропускаем.
                    if node_id in self.saved_messages:
                        last_msg = self.saved_messages[node_id]
                        if last_msg.text == message_text:
                            continue

                    chat_with = msg.find("div", {"class": "media-user-name"}).text
                    message_obj = types.Message(message_text, node_id, chat_with, unread)
                    if self.first_request:
                        event = types.InitialMessageEvent(message_obj, self.last_message_event_tag)
                    else:
                        event = types.NewMessageEvent(message_obj, self.last_message_event_tag)
                    events.append(event)
                    self.saved_messages[message_obj.node_id] = message_obj

            elif obj.get("type") == "orders_counters":
                self.last_order_event_tag = obj.get("tag")
                if not self.first_request:
                    events.append(types.OrdersListChangedEvent(obj["data"]["buyer"], obj["data"]["seller"],
                                                               self.last_order_event_tag))
                attempts = 3
                while attempts:
                    try:
                        orders_list = self.account.get_orders(include_outstanding=True, include_refund=True,
                                                              include_completed=True)
                        break
                    except exceptions.StatusCodeIsNot200 as e:
                        logger.error(e)
                        attempts -= 1
                        time.sleep(1)
                    except:
                        logger.error("Не удалось обновить список ордеров.")
                        logger.debug(traceback.format_exc())
                        attempts -= 1
                        time.sleep(1)
                if not attempts:
                    logger.error("Не удалось обновить список ордеров: превышено кол-во попыток.")
                    return []

                for order in orders_list:
                    if order.id not in self.saved_orders:
                        if self.first_request:
                            event = types.InitialOrderEvent(order, self.last_order_event_tag)
                            events.append(event)
                        else:
                            event = types.NewOrderEvent(order, self.last_order_event_tag)
                            events.append(event)
                            if order.status == types.OrderStatuses.COMPLETED:
                                event2 = types.OrderStatusChangedEvent(order, self.last_order_event_tag)
                                events.append(event2)
                        self.update_saved_order(order)
                    elif order.status != self.saved_orders[order.id].status:
                        event = types.OrderStatusChangedEvent(order_obj=order, tag=self.last_order_event_tag)
                        events.append(event)
                        self.update_saved_order(order)

        if self.first_request:
            self.first_request = False

        return events

    def update_saved_message(self, message_obj: types.Message) -> None:
        """
        Обновляет последнее сохраненное сообщение.

        :param message_obj: экземпляр класса, описывающего сообщение.
        """
        message_copy = deepcopy(message_obj)
        message_copy.text = message_copy.text[:250]
        self.saved_messages[message_copy.node_id] = message_copy

    def update_saved_order(self, order: types.Order) -> None:
        """
        Обновляет последнее сохраненное состояние заказа.

        :param order: экземпляр класса, описывающего заказа.
        """
        self.saved_orders[order.id] = order

    def listen(self, delay: float | int = 6.0, ignore_exceptions: bool = True) \
            -> Iterator[types.Event]:
        """
        "Слушает" FunPay в ожидании новых событий.

        :param delay: задержка между запросами.

        :param ignore_exceptions: игнорировать ошибки при выполнении запросов.
        """
        if not self.account.is_authorized():
            raise exceptions.NotAuthorized()

        while True:
            try:
                updates = self.get_updates()
                for event in updates:
                    yield event
            except Exception as e:
                if not ignore_exceptions:
                    raise e
                else:
                    logger.error("Произошла ошибка при получении событий "
                                 "(ничего страшного, если это сообщение появляется нечасто).")
                    logger.debug(traceback.format_exc())
            time.sleep(delay)
