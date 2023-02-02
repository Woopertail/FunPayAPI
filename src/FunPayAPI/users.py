"""
В данном модуле написаны функции, которые позволяют получать информацию о пользователях без использования golden_key
"""

from bs4 import BeautifulSoup
import requests
import logging

from . import exceptions
from . import types


logger = logging.getLogger("FunPayAPI.users")


def get_user(user_id: int, include_currency: bool = False, user_agent: str = "", timeout: float = 10.0) -> types.UserInfo:
    """
    Получает полную информацию о лотах и категориях пользователя.

    :param user_id: ID пользователя.

    :param include_currency: включать ли в список категории / лоты, относящиеся к игровой валюте.

    :param user_agent: user-agent.

    :param timeout: тайм-аут ожидания ответа.

    :return: экземпляр класса с информацией о пользователе.
    """
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "user-agent": user_agent
    }
    response = requests.get(f"{types.Links.USER}/{user_id}/", headers=headers, timeout=timeout)
    logger.debug(response.status_code)
    if response.status_code == 404:
        raise Exception("Пользователь не найден.")  # todo: создать и добавить кастомное исключение: пользователя не существует.
    if response.status_code != 200:
        raise exceptions.StatusCodeIsNot200(response.status_code)

    html_response = response.content.decode()
    logger.debug(html_response)
    parser = BeautifulSoup(html_response, "html.parser")
    categories = []
    lots = []

    # Если категорий не найдено - возвращаем пустые списки
    category_divs = parser.find_all("div", {"class": "offer-list-title-container"})
    if category_divs is None:
        return types.UserInfo([], [])

    # Парсим категории
    for div in category_divs:
        info_div = div.find("div", {"class": "offer-list-title"})
        category_link = info_div.find("a")
        public_link = category_link["href"]
        if "chips" in public_link:
            # 'chips' в ссылке означает, что данная категория - игровая валюта.
            # Например: https://funpay.com/chips/125/ - Серебро Black Desert Mobile.
            if not include_currency:
                continue
            category_type = types.CategoryTypes.CURRENCY
        else:
            category_type = types.CategoryTypes.LOT

        edit_lots_link = public_link + "trade"
        title = category_link.text
        category_id = int(public_link.split("/")[-2])
        category_object = types.Category(id_=category_id, game_id=None, title=title, edit_lots_link=edit_lots_link,
                                         public_link=public_link, type_=category_type)
        categories.append(category_object)

        # Парсим лоты внутри текущей категории
        lot_divs = div.parent.find_all("a", {"class": "tc-item"})
        for lot_div in lot_divs:
            lot_id = int(lot_div["href"].split("id=")[1])
            lot_title = lot_div.find("div", {"class": "tc-desc-text"}).text
            price = lot_div.find("div", {"class": "tc-price"})["data-s"]

            lot_obj = types.Lot(category_id, None, lot_id, lot_title, price)
            lots.append(lot_obj)

    return types.UserInfo(lots, categories)
