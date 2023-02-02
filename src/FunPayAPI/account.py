from bs4 import BeautifulSoup
import requests
import json
import time
import logging

from . import types
from . import exceptions
from . import utils


logger = logging.getLogger("FunPayAPI.account")


class Account:
    """
    Класс для работы с аккаунтом FunPay.
    """
    def __init__(self, golden_key: str, user_agent: str = "", timeout: float | int = 10.0):
        """
        :param golden_key: токен аккаунта.

        :param user_agent: user-agent браузера, с которого был произведен вход в аккаунт.

        :param timeout: тайм-аут ожидания ответа на запросы.
        """
        self.golden_key: str = golden_key
        self.user_agent = user_agent
        self.timeout: float = timeout
        self.__authorized: bool = False

        self.html: str | None = None
        self.app_data: dict | None = None
        self.id: int | None = None
        self.username: str | None = None
        self.balance: int | None = None
        self.currency: str | None = None
        self.active_orders: int | None = None

        self.csrf_token: str | None = None
        self.session_id: str | None = None
        self.last_update: int | None = None

        self.saved_html_chats: str | None = None

    def get(self, update_session_id: bool = False):
        """
        Получает / обновляет данные об аккаунте.

        :param update_session_id: обновить self.session_id или использовать старый.
        """
        headers = {
            "cookie": f"golden_key={self.golden_key}",
            "user-agent": self.user_agent
        }
        if self.session_id and not update_session_id:
            headers["cookie"] += f"; PHPSESSID={self.session_id}"

        response = requests.get(types.Links.BASE_URL, headers=headers, timeout=self.timeout)
        logger.debug(f"Статус-код получения данных об аккаунте: {response.status_code}.")
        if response.status_code != 200:
            raise exceptions.StatusCodeIsNot200(response.status_code)

        html_response = response.content.decode()
        # logger.debug(f"HTML аккаунта: {html_response}")
        soup = BeautifulSoup(html_response, "html.parser")

        username = soup.find("div", {"class": "user-link-name"})
        if username is None:
            raise exceptions.AccountDataNotfound()

        username = username.text
        app_data = json.loads(soup.find("body")["data-app-data"])
        userid = app_data["userId"]
        csrf_token = app_data["csrf-token"]

        active_orders = soup.find("span", {"class": "badge badge-trade"})
        active_orders = int(active_orders.text) if active_orders else 0

        balance_badge = soup.find("span", {"class": "badge badge-balance"})
        balance = float(balance_badge.text.split(" ")[0]) if balance_badge else 0
        currency = balance_badge.text.split(" ")[1] if balance_badge else ""

        cookies = response.cookies.get_dict()
        if (update_session_id and self.session_id) or not self.session_id:
            session_id = cookies["PHPSESSID"]
            self.session_id = session_id

        self.html = html_response
        self.app_data = app_data
        self.id = userid
        self.username = username
        self.balance = balance
        self.currency = currency
        self.active_orders = active_orders
        self.csrf_token = csrf_token
        self.last_update = int(time.time())
        self.__authorized = True
        return self

    def get_orders(self, include_outstanding: bool = True,
                   include_completed: bool = False,
                   include_refund: bool = False,
                   exclude: list[str] | None = None) -> list[types.Order]:
        """
        Получает список ордеров на аккаунте.

        :param include_outstanding: включить в список оплаченные (но незавершенные) заказы.

        :param include_completed: включить в список завершенные заказы.

        :param include_refund: включить в список заказы, за которые оформлен возврат.

        :param exclude: список ID заказов, которые нужно исключить из итогового списка.

        :return: Список с заказами.
        """
        if not self.is_authorized():
            raise exceptions.NotAuthorized()

        exclude = [] if not exclude else exclude
        headers = {"cookie": f"golden_key={self.golden_key}; PHPSESSID={self.session_id};",
                   "user-agent": self.user_agent}

        response = requests.get(types.Links.ORDERS, headers=headers, timeout=self.timeout)
        logger.debug(f"Статус-код получения ордеров: {response.status_code}.")
        if response.status_code != 200:
            raise exceptions.StatusCodeIsNot200(response.status_code)

        html_response = response.content.decode()
        logger.debug(f"Ответ от FunPay (информация об ордерах): {html_response}")
        soup = BeautifulSoup(html_response, "html.parser")

        check_user = soup.find("div", {"class": "user-link-name"})
        if check_user is None:
            raise exceptions.AccountDataNotfound()

        order_divs = soup.find_all("a", {"class": "tc-item"})
        if order_divs is None:
            return []
        orders_list = []

        for div in order_divs:
            classname = div.get("class")
            if "warning" in classname:
                if not include_refund:
                    continue
                status = types.OrderStatuses.REFUND
            elif "info" in classname:
                if not include_outstanding:
                    continue
                status = types.OrderStatuses.OUTSTANDING
            else:
                if not include_completed:
                    continue
                status = types.OrderStatuses.COMPLETED

            order_id = div.find("div", {"class": "tc-order"}).text
            if order_id in exclude:
                continue

            title = div.find("div", {"class": "order-desc"}).find("div").text
            price = float(div.find("div", {"class": "tc-price"}).text.split(" ")[0])

            buyer_div = div.find("div", {"class": "media-user-name"}).find("span")
            buyer_username = buyer_div.text
            buyer_id = int(buyer_div.get("data-href")[:-1].split("https://funpay.com/users/")[1])

            order = types.Order(html=str(div), id_=order_id, title=title, price=price, buyer_username=buyer_username,
                                buyer_id=buyer_id, status=status)
            orders_list.append(order)
        return orders_list

    def send_message(self, message_obj: types.Message) -> dict:
        """
        Отправляет сообщение.

        :param message_obj: экземпляр класса, описывающий сообщение.

        :return: ответ FunPay.
        """
        headers = {
            "accept": "*/*",
            "cookie": f"golden_key={self.golden_key}; PHPSESSID={self.session_id}",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "user-agent": self.user_agent,
            "referer": f"https://funpay.com/chat/?node={message_obj.node_id}",
            "origin": f"https://funpay.com"
        }
        request = {
            "action": "chat_message",
            "data": {
                "node": message_obj.node_id,
                "last_message": -1,
                "content": message_obj.text
            }
        }
        objects = [
            {"type": "chat_node",
             "id": message_obj.node_id,
             "tag": "00000000",
             "data": {
                 "node": message_obj.node_id,
                 "last_message": -1,
                 "content": ""}
             }
        ]
        payload = {
            "objects": json.dumps(objects),
            "request": json.dumps(request),
            "csrf_token": self.csrf_token
        }
        response = requests.post(types.Links.RUNNER, headers=headers, data=payload, timeout=self.timeout)
        logger.debug(f"Статус-код отправления сообщения: {response.status_code}.")
        if response.status_code != 200:
            raise exceptions.StatusCodeIsNot200(response.status_code)

        json_response = response.json()
        logger.debug(f"Ответ от FunPay (отправление сообщения): {json_response}")
        if json_response.get("response"):
            if json_response.get("response").get("error") is not None:
                raise exceptions.MessageNotDelivered(json_response)
            return json_response
        else:
            raise exceptions.MessageNotDelivered(json_response)

    def get_node_id_by_username(self, username: str, force_request: bool = False) -> int | None:
        """
        Парсит self.chats_html и ищет node_id чата по username'у.
        todo: Если self.chats_html is None -> делает запрос к FunPay.

        :param username: никнейм пользователя (искомого чата).

        :param force_request: todo: пропустить ли поиск в self.chats_html и отправить ли сразу запрос к FunPay.

        :return: node_id чата или None, если чат не найден.
        """
        if not force_request and self.saved_html_chats is not None:
            parser = BeautifulSoup(self.saved_html_chats, "html.parser")
            user_box = parser.find("div", {"class": "media-user-name"}, text=username)
            if user_box is not None:
                node_id = user_box.parent["data-id"]
                return int(node_id)
        return None

    def get_category_game_id(self, category: types.Category) -> int:
        """
        Получает ID игры, к которой относится категория.

        :param category: экземпляр класса Category.

        :return: ID игры, к которой относится категория.
        """
        if category.type == types.CategoryTypes.LOT:
            link = f"{types.Links.BASE_URL}/lots/{category.id}/trade"
        else:
            link = f"{types.Links.BASE_URL}/chips/{category.id}/trade"

        headers = {"cookie": f"golden_key={self.golden_key}",
                   "user-agent": self.user_agent}
        response = requests.get(link, headers=headers, timeout=self.timeout)
        logger.debug(f"Статус-код получения ордеров: {response.status_code}.")
        if response.status_code == 404:
            raise Exception("Категория не найдена.")  # todo: создать кастомное исключение: категория не найдена.
        if response.status_code != 200:
            raise exceptions.StatusCodeIsNot200(response.status_code)

        html_response = response.content.decode()
        # logger.debug(f"Ответ от FunPay (запрос game_id категории): {html_response}")
        parser = BeautifulSoup(html_response, "html.parser")

        if parser.find("div", {"class": "user-link-name"}) is None:
            raise exceptions.AccountDataNotfound()

        if category.type == types.CategoryTypes.LOT:
            game_id = int(parser.find("div", {"class": "col-sm-6"}).find("button")["data-game"])
        else:
            game_id = int(parser.find("input", {"name": "game"})["value"])

        return game_id

    def get_lot_info(self, lot_id: int, game_id: int) -> dict[str, str]:
        """
        Получает значения всех полей лота (в окне редактирования лота).

        :param lot_id: ID лота.

        :param game_id: ID игры, к которой относится лот.

        :return: словарь {"название поля": "значение поля"}.
        """
        headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "x-requested-with": "XMLHttpRequest",
            "cookie": f"golden_key={self.golden_key}; PHPSESSID={self.session_id}",
            "user-agent": self.user_agent
        }
        tag = utils.gen_random_tag()
        payload = {
            "tag": tag,
            "offer": lot_id,
            "node": game_id
        }
        query = f"?tag={tag}&offer={lot_id}&node={game_id}"

        response = requests.get(f"{types.Links.BASE_URL}/lots/offerEdit{query}", headers=headers, data=payload)
        logger.debug(f"Статус-код получения данных о лоте: {response.status_code}")
        if not response.status_code == 200:
            raise exceptions.StatusCodeIsNot200(response.status_code)
        json_response = response.json()
        logger.debug(f"Ответ от FunPay (получение данных о лоте): {json_response}")
        parser = BeautifulSoup(json_response["html"], "html.parser")

        input_fields = parser.find_all("input")
        text_fields = parser.find_all("textarea")
        selection_fields = parser.find_all("select")
        result = {}

        for field in input_fields:
            name = field["name"]
            value = field.get("value")
            if value is None:
                value = ""
            result[name] = value

        for field in text_fields:
            name = field["name"]
            value = field.text
            if not value:
                value = ""
            result[name] = value

        for field in selection_fields:
            name = field["name"]
            value = field.find("option", selected=True)["value"]
            result[name] = value

        return result

    def save_lot(self, lot_info: dict[str, str], active: bool = True) -> dict:
        """
        Сохраняет лот.

        :param lot_info: информация о полях лота, получаемая с помощью метода get_lot_info().

        :param active: сделать ли лот активным.

        :return: ответ FunPay.
        """
        lot_info["location"] = "trade"
        if active:
            lot_info["active"] = "on"
        else:
            if lot_info.get("active") is not None:
                lot_info.pop("active")

        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "cookie": f"golden_key={self.golden_key}; PHPSESSID={self.session_id}",
            "user-agent": self.user_agent
        }
        response = requests.post(f"{types.Links.BASE_URL}/lots/offerSave", headers=headers, data=lot_info)
        logger.debug(f"Статус-код изменения состояния лота: {response.status_code}.")
        if response.status_code != 200:
            raise exceptions.StatusCodeIsNot200(response.status_code)

        json_response = response.json()
        logger.debug(f"Ответ от FunPay (сохранение лота): {json_response}")
        if json_response.get("error"):
            raise exceptions.LotNotUpdated(json_response)
        return json_response

    def request_lots_raise(self, category: types.Category) -> dict:
        """
        Отправляет запрос на получение modal-формы для поднятия лотов категории category.id.
        !ВНИМЕНИЕ! Для отправки запроса необходимо, чтобы category.game_id != None.
        !ВНИМАНИЕ! Если на аккаунте только 1 категория, относящаяся к игре category.game_id,
        то FunPay поднимет данную категорию в списке без отправления modal-формы с выбором других категорий.

        :param category: экземпляр класса, описывающий поднимаемую категорию.

        :return: ответ FunPay.
        """
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "cookie": f"locale=ru; golden_key={self.golden_key}",
            "x-requested-with": "XMLHttpRequest",
            "user-agent": self.user_agent
        }
        payload = {
            "game_id": category.game_id,
            "node_id": category.id
        }

        response = requests.post(types.Links.RAISE, headers=headers, data=payload, timeout=self.timeout)
        logger.debug(f"Статус-код получения данных для поднятия лотов: {response.status_code}.")
        if response.status_code != 200:
            raise exceptions.StatusCodeIsNot200(response.status_code)
        json_response = response.json()
        logger.debug(f"Ответ от FunPay (запрос modal-формы поднятия лотов): {json_response}")
        return json_response

    def raise_game_categories(self, category: types.Category, exclude: list[int] | None = None) -> types.RaiseResponse:
        """
        Поднимает лоты всех категорий игры category.game_id.
        !ВНИМЕНИЕ! Для поднятия лотов необходимо, чтобы category.game_id != None.

        :param category: экземпляр класса, описывающий поднимаемую категорию.

        :param exclude: список ID категорий, которые не нужно поднимать.

        :return: ответ FunPay.
        """
        check = self.request_lots_raise(category)
        if check.get("error") and check.get("msg") and "Подождите" in check.get("msg"):
            wait_time = utils.get_wait_time_from_raise_response(check.get("msg"))
            return types.RaiseResponse(False, wait_time, [], check)
        elif check.get("error"):
            # Если вернулся ответ с ошибкой и это не "Подождите n времени" - значит творится какая-то дичь.
            return types.RaiseResponse(False, 10, [], check)
        elif check.get("error") is not None and not check.get("error"):
            # Если была всего 1 категория и FunPay ее поднял без отправки modal-окна
            return types.RaiseResponse(True, 3600, [category.title], check)
        elif check.get("modal"):
            # Если же появилась модалка, то парсим все чекбоксы и отправляем запрос на поднятие всех категорий, кроме тех,
            # которые в exclude.
            parser = BeautifulSoup(check.get("modal"), "html.parser")
            category_ids = []
            category_names = []
            checkboxes = parser.find_all("div", {"class": "checkbox"})
            for cb in checkboxes:
                category_id = int(cb.find("input")["value"])
                if exclude is None or category_id not in exclude:
                    category_ids.append(category_id)
                    category_name = cb.find("label").text
                    category_names.append(category_name)

            headers = {
                "accept": "*/*",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                "cookie": f"locale=ru; golden_key={self.golden_key}",
                "x-requested-with": "XMLHttpRequest",
                "user-agent": self.user_agent
            }
            payload = {
                "game_id": category.game_id,
                "node_id": category.id,
                "node_ids[]": category_ids
            }
            response = requests.post(types.Links.RAISE, headers=headers, data=payload, timeout=self.timeout)
            logger.debug(f"Статус-код поднятия лотов: {response.status_code}.")
            if not response.status_code == 200:
                raise exceptions.StatusCodeIsNot200(response.status_code)
            json_response = response.json()
            logger.debug(f"Ответ FunPay (поднятие категорий): {json_response}.")
            if not json_response.get("error"):
                return types.RaiseResponse(True, 3600, category_names, json_response)
            else:
                return types.RaiseResponse(False, 10, [], json_response)

    def refund_order(self, order_id: str) -> None:
        """
        Оформляет возврат средств за заказ.

        :param order_id: ID заказа.
        """

        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "cookie": f"golden_key={self.golden_key}; PHPSESSID={self.session_id}",
            "user-agent": self.user_agent
        }

        payload = {
            "id": order_id,
            "csrf_token": self.csrf_token
        }
        response = requests.post(types.Links.REFUND, headers=headers, data=payload, timeout=self.timeout)
        if not response.status_code == 200:
            raise exceptions.StatusCodeIsNot200(response.status_code)

    def is_authorized(self):
        return self.__authorized

    def update_chats(self, chats_html: str):
        """
        Обновляет сохраненный HTML чатов (для get_node_id_by_username)

        :param chats_html: HTML чатов.
        """
        self.saved_html_chats = chats_html
