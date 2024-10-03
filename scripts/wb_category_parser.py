import asyncio
from math import floor
import requests
# import json
import pandas as pd
from retry import retry
# pip install openpyxl
# pip install xlsxwriter


def get_catalogs_wb() -> dict:
    """получаем полный каталог Wildberries"""
    url = 'https://static-basket-01.wbbasket.ru/vol0/data/main-menu-ru-ru-v2.json'
    headers = {'Accept': '*/*', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    return requests.get(url, headers=headers).json()


def get_data_category(catalogs_wb: dict) -> list:
    """сбор данных категорий из каталога Wildberries"""
    catalog_data = []
    if isinstance(catalogs_wb, dict) and 'childs' not in catalogs_wb:
        catalog_data.append({
            'name': f"{catalogs_wb['name']}",
            'shard': catalogs_wb.get('shard', None),
            'url': catalogs_wb['url'],
            'query': catalogs_wb.get('query', None)
        })
    elif isinstance(catalogs_wb, dict):
        catalog_data.append({
            'name': f"{catalogs_wb['name']}",
            'shard': catalogs_wb.get('shard', None),
            'url': catalogs_wb['url'],
            'query': catalogs_wb.get('query', None)
        })
        catalog_data.extend(get_data_category(catalogs_wb['childs']))
    else:
        for child in catalogs_wb:
            catalog_data.extend(get_data_category(child))
    return catalog_data


def search_category_in_catalog(url: str, catalog_list: list) -> dict:
    """проверка пользовательской ссылки на наличии в каталоге"""
    for catalog in catalog_list:
        if catalog['url'] == url.split('https://www.wildberries.ru')[-1]:
            return catalog


def get_data_from_json(json_file: dict) -> list:
    """извлекаем из json данные"""
    data_list = []
    for data in json_file['data']['products']:
        sku = data.get('id')
        name = data.get('name')
        price = int(data.get("priceU") / 100)
        salePriceU = int(data.get('salePriceU') / 100)
        price_wb = floor(salePriceU * 0.97)
        sale = data.get('sale')
        totalQuantity = data.get('totalQuantity')
        brand = data.get('brand')
        rating = data.get('rating')
        supplier = data.get('supplier')
        supplierRating = data.get('supplierRating')
        feedbacks = data.get('feedbacks')
        reviewRating = data.get('reviewRating')
        promoTextCard = data.get('promoTextCard')
        promoTextCat = data.get('promoTextCat')
        data_list.append({
            'Артикул': sku,
            'Название': name,
            'Цена со скидкой': salePriceU,
            'С вб кошельком': price_wb,
            'До скидки': price,
            '% скидки': sale,
            'Остатки': totalQuantity,
            'Бренд': brand,
            'Рейтинг': rating,
            'Продавец': supplier,
            'Рейтинг продавца': supplierRating,
            'Отзывов': feedbacks,
            'Рейтинг отзывов': reviewRating,
            'Ссылка': f'https://www.wildberries.ru/catalog/{data.get("id")}/detail.aspx?targetUrl=BP',
            'Акция': promoTextCard,
            'promoTextCat': promoTextCat
        })
    return data_list


@retry(Exception, tries=-1, delay=0)
def scrap_page(page: int, shard: str, query: str, low_price: int, top_price: int, discount: int = None) -> dict:
    """Сбор данных со страниц"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0)"}
    url = f'https://catalog.wb.ru/catalog/{shard}/catalog?appType=1&curr=rub' \
          f'&dest=-1257786' \
          f'&locale=ru' \
          f'&page={page}' \
          f'&priceU={low_price * 100};{top_price * 100}' \
          f'&sort=popular&spp=0' \
          f'&{query}' \
          f'&discount={discount}'
    r = requests.get(url, headers=headers)
    return r.json()


def save_excel(data: list, filename: str):
    """сохранение результата в excel файл"""
    df = pd.DataFrame(data)
    writer = pd.ExcelWriter(f'results/{filename}.xlsx')
    df.to_excel(writer, sheet_name='data', index=False)
    # указываем размеры каждого столбца в итоговом файле
    writer.sheets['data'].set_column(0, 1, width=10)  # артикул
    writer.sheets['data'].set_column(1, 2, width=34)  # название
    writer.sheets['data'].set_column(2, 3, width=16)  # цена со скидкой
    writer.sheets['data'].set_column(3, 4, width=16)  # цена с вб кошельком
    writer.sheets['data'].set_column(4, 5, width=10)  # цена до скидки
    writer.sheets['data'].set_column(5, 6, width=9)  # скидка
    writer.sheets['data'].set_column(6, 7, width=8)  # остатки
    writer.sheets['data'].set_column(7, 8, width=16)  # бренд
    writer.sheets['data'].set_column(8, 9, width=8)  # рейтинг
    writer.sheets['data'].set_column(9, 10, width=25)  # продавец
    writer.sheets['data'].set_column(10, 11, width=17)  # рейтинг продавца
    writer.sheets['data'].set_column(11, 12, width=8)  # отзывов
    writer.sheets['data'].set_column(12, 13, width=16)  # рейтинг отзывов
    writer.sheets['data'].set_column(13, 14, width=14)  # ссылка
    writer.sheets['data'].set_column(13, 14, width=10)  # акция
    writer.sheets['data'].set_column(13, 14, width=13)  # promoTextCat
    writer.close()
    return f"results/{filename}.xlsx"


async def parser(url: str, low_price: int, top_price: int, discount: int):
    """парсер по введенной категории, опционально ценовой диапазон"""
    catalog_data = get_data_category(get_catalogs_wb())  # получаем данные по заданному каталогу
    try:
        category = search_category_in_catalog(url=url, catalog_list=catalog_data)  # поиск категории в общем каталоге
        data_list = []
        for page in range(1, 51):  # вб отдает 50 страниц товара (раньше было 100)
            await asyncio.sleep(0.01)
            data = scrap_page(
                page=page,
                shard=category['shard'],
                query=category['query'],
                low_price=low_price,
                top_price=top_price,
                discount=discount)
            if len(get_data_from_json(data)) > 0:
                data_list.extend(get_data_from_json(data))
            else:
                break
        return save_excel(data_list, filename=f'{category["name"]}_from_{low_price}_to_{top_price}')
    except TypeError:
        return None

