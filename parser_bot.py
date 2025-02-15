import telebot
import requests
import os
import time
import csv
import json
import pandas as pd
from seleniumbase import Driver
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent

load_dotenv() 

TOKEN=os.getenv('TOKEN')
BRICKOGNIZE_API_URL = "https://api.brickognize.com/predict/"


bot = telebot.TeleBot(TOKEN)

else_parsed_data = []
parsed_data = []
lego_details = {}

@bot.message_handler(commands=['start'])
def start(message):
    reset_session_data()
    bot.send_message(message.chat.id, "Здравствуйте! Пожалуйста, пришлите мне фотографию набора, минифигурки или детали LEGO, и я постараюсь идентифицировать его для вас. Желательно, чтобы фото было на однотонном фоне и хорошего качества.")

@bot.message_handler(commands=['reset'])
def restart(message):
    reset_session_data()
    bot.send_message(message.chat.id, "Перезапускаем бота...")
    start(message) 

def reset_session_data():
    global parsed_data, lego_details, else_parsed_data
    else_parsed_data = []
    parsed_data = []
    lego_details = {}  


@bot.message_handler(content_types=['photo'])
def handle_photo(message):

    file_info = bot.get_file(message.photo[-1].file_id)
    

    downloaded_file = bot.download_file(file_info.file_path)


    user_id = message.from_user.id
    photo_path = f"temp_{user_id}.jpeg"
    with open(photo_path, 'wb') as new_file:
        new_file.write(downloaded_file)


    lego_details = process_lego_image(photo_path)


    if lego_details:
        name = lego_details.get('name', 'Unknown')
        lego_id = lego_details.get('id', 'Unknown')
        url = lego_details.get('external_sites')[0]['url']

 
        response_message = f"Найденный товар:\nНазвание: {name}\nID: {lego_id}\nURL: {url}\n\nНа какой площадке Вы хотите найти данный товар: Авито, Ebricks, Kuboteka?"
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add('Авито', 'Ebricks', 'Kuboteka')
        bot.send_message(message.chat.id, response_message, reply_markup=markup)


        bot.register_next_step_handler(message, handle_resource_choice, lego_details)
    else:
        response_message = "Простите, невозможно определить Lego. Перешлите другое изображение."
        bot.send_message(message.chat.id, response_message)


    os.remove(photo_path)


def process_lego_image(photo_path: str):
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with open(photo_path, 'rb') as image_file:
                files = {'query_image': (photo_path, image_file, 'image/jpeg')}
                response = requests.post(BRICKOGNIZE_API_URL, files=files, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    return data['items'][0]
                else:
                    print("Не найдено.")
                    return None
            else:
                print(f"Запрос не выполнен с кодом состояния: {response.status_code}")
                print(response.text)
                return None

        except requests.exceptions.ConnectionError as e:
            print(f"Ошибка подключения при попытке {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2) 
            else:
                print("Достигнуто максимальное количество повторных попыток. Не удалось подключиться к API.")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Запросить исключение при попытке {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                print("Достигнуто максимальное количество повторных попыток. Не удалось подключиться к API.")
                return None
        except Exception as e:
            print(f"Ошибка при обработке изображения: {e}")
            return None
    return None


def handle_resource_choice(message, lego_details):
    if message.text.lower() == 'авито':
        name = lego_details.get('name', '')
        lego_id = lego_details.get('id', '')
        query = f"{name} {lego_id}"
        bot.send_message(message.chat.id, f"Ищу: {query} на Авито...")
        avito_data = search_avito(query) or []
        parsed_data.extend(avito_data)
        ask_for_format(message)
    elif message.text.lower() == 'ebricks':
        lego_id = lego_details.get('id', '')
        query = f"{lego_id}"
        bot.send_message(message.chat.id, f"Ищу: {query} на Ebricks...")
        ebricks_data = ebricks(query) or []
        else_parsed_data.extend(ebricks_data)
        ask_for_format(message)
    # elif message.text.lower() == 'lekub':
    #     lego_id = lego_details.get('id', '')
    #     query = f"{lego_id}"
    #     bot.send_message(message.chat.id, f"Ищу: {query} на Lekub...")
    #     lekub_data = lekub(query) or []
    #     else_parsed_data.extend(lekub_data)
    #     ask_for_format(message)
    elif message.text.lower() == 'kuboteka':
        lego_id = lego_details.get('id', '')
        query = f"{lego_id}"
        bot.send_message(message.chat.id, f"Ищу: {query} на Kuboteka...")
        kuboteka_data = kuboteka(query) or []
        else_parsed_data.extend(kuboteka_data)
        ask_for_format(message)
    else:
        bot.send_message(message.chat.id, "Некорректный выбор. Выберите из Авито, Ebricks, Lekub, Kuboteka")
        bot.register_next_step_handler(message, handle_resource_choice, lego_details)

def ask_for_format(message):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add('Вывести результаты в Telegram', 'Сохранить в формате JSON', 'Сохранить в формате CSV')
    bot.send_message(message.chat.id, "Как бы вы хотели получить данные?", reply_markup=markup)
    bot.register_next_step_handler(message, handle_save_format)

def search_avito(query: str):
    try:
        driver = Driver(uc=True)
        driver.uc_open_with_reconnect(f'https://www.avito.ru/moskva?q={query}', reconnect_time=6)
        driver.uc_gui_click_captcha()

        listings = []
        items = driver.find_elements(By.CSS_SELECTOR, '.items-items-pZX46')
        
        for item in items:
            name = item.find_element(By.CSS_SELECTOR, "[itemprop='name']").text
            link = item.find_element(By.CSS_SELECTOR, "[itemprop='url']").get_attribute('href')
            price = item.find_element(By.CSS_SELECTOR, "[itemprop='price']").get_attribute('content')
            description = item.find_element(By.CSS_SELECTOR, "[itemprop='description']").get_attribute('content')
        
            listings.append({
                'name': name,
                'description': description,
                'price': price,
                'url': link
            })
        
        driver.quit()
        if not listings:
                return [] 
        return listings
    
    except Exception as e:
        print(f"Ошибка во время парсинга Авито: {e}")
        driver.quit()
        return []
    
def ebricks(ebricks_search):
    data_list = []
    try:
        ua = UserAgent()
        options = webdriver.ChromeOptions()
        options.add_argument(f"--user-agent={ua.random}")
        options.add_argument("--headless")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        url = f"https://ebricks.ru/products/search?sort=0&balance=&categoryId=&min_cost=&max_cost=&page=1&text={ebricks_search}"
        driver.get(url)

        product_divs = driver.find_elements(By.CLASS_NAME, "product-item.text-center.medium-text-left")
        if product_divs:
            for div in product_divs:
                text = div.text
                link_element = div.find_element(By.CLASS_NAME, "product-item__preview")
                link = link_element.get_attribute("href") if link_element else ""

                data = {"count": text.split('\n')[0].split(':')[-1],
                        'name': text.split('\n')[1],
                        'price': text.split('\n')[2],
                        "link": link}
                data_list.append(data)
                if not data_list:
                    return [] 
                return data_list
        else:
            print("Товары не найдены.")
            return

    finally:
        driver.quit()

# def lekub(query):
#     data_list = []
#     try:
#         ua = UserAgent()
#         options = webdriver.ChromeOptions()
#         options.add_argument(f"--user-agent={ua.random}")  # Добавление случайного user-agent
#         options.add_argument("--headless")  # Запуск в фоновом режиме (без GUI)
#         driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
#         url = f"https://lekub.ru/search/?keyword={query}"
#         driver.get(url)

#         no_results = driver.find_elements(By.XPATH, "//p[text()='Нет товаров, соответствующих критериям поиска.']")
#         if no_results:
#             print("Таких деталей нет.")
#             return

#         item_elements = driver.find_elements(By.XPATH, "//div[@itemprop='itemListElement']")
#         for item in item_elements:
#             h2_element = item.find_element(By.TAG_NAME, "h2")
#             name = h2_element.text if h2_element else ""

#             if query.lower() not in name.lower():
#                 continue

#             link_element = item.find_element(By.CLASS_NAME, "pinfo").find_element(By.TAG_NAME, "a")
#             link = link_element.get_attribute("href") if link_element else ""

#             price_element = item.find_element(By.CLASS_NAME, "tovar-footer")
#             price = price_element.text if price_element else ""
#             price_lego = 0
#             if price != 'нет в наличии':
#                 if len(price.split('\n')) > 2:
#                     price_lego = price.split('\n')[1]
#                 else:
#                     price_lego = price.split('\n')[0]

#             data = {"count": (0 if price == 'нет в наличии' else 1),
#                     'name': name,
#                     'price': price_lego,
#                     "link": link}
#             data_list.append(data)
#             if not data_list:
#                 return [] 
#             return data_list

#     finally:
#         driver.quit()

def kuboteka(search_query):
    data_list = []
    try:
        ua = UserAgent()
        options = webdriver.ChromeOptions()
        options.add_argument(f"--user-agent={ua.random}")  # Добавление случайного user-agent
        options.add_argument("--headless")  # Запуск в фоновом режиме (без GUI)
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        url = f"https://kuboteka.shop/search/?search={search_query}"
        driver.get(url)

        no_results = driver.find_elements(By.XPATH, "//p[text()='Нет товаров, соответствующих критериям поиска.']")
        if no_results:
            print('Нет результатов.')
            return

        product_div = driver.find_element(By.CLASS_NAME, "product__card__inner")

        link_element = driver.find_element(By.CLASS_NAME, "product__card__image")
        link = link_element.get_attribute("href") if link_element else ""

        name_element = product_div.find_element(By.XPATH, ".//span[@itemprop='name']")
        name = name_element.text if name_element else ""

        data = {"count": product_div.text.split('\n')[-1].split(':')[-1].split(' ')[-2],
                'name': name,
                'price': product_div.text.split('\n')[3],
                "link": link}
        data_list.append(data)
        if not data_list:
            return [] 
        return data_list
    finally:
        driver.quit()

def handle_save_format(message):
    if message.text.lower() == 'вывести результаты в telegram':
        for result in parsed_data:
            response_message = f"Название: {result['name']}\nОписание: {result['description']}\nЦена: {result['price']}\nURL: {result['url']}"
            bot.send_message(message.chat.id, response_message)
        for result in else_parsed_data:
            response_message = f"Название: {result['name']}\nКоличество: {result['count']}\nЦена: {result['price']}\nURL: {result['link']}"
            bot.send_message(message.chat.id, response_message)
    elif message.text.lower() == 'сохранить в формате json':
        if parsed_data:
            save_as_json(parsed_data, message)
        else:
            save_as_json(else_parsed_data, message)
    elif message.text.lower() == 'сохранить в формате csv':
        if parsed_data:
            save_as_csv(parsed_data, message)
        else:
            save_as_csv(else_parsed_data, message)
    reset_session_data()

def save_as_json(data, message):
    json_filename = 'data.json'
    with open(json_filename, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    

    with open(json_filename, 'rb') as file:
        bot.send_document(message.chat.id, file)

    os.remove(json_filename)

def save_as_csv(data, message):
    csv_filename = 'data.csv'
    keys = data[0].keys()
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

    with open(csv_filename, 'rb') as file:
        bot.send_document(message.chat.id, file)
    
    os.remove(csv_filename)

bot.infinity_polling(timeout=10, long_polling_timeout = 5)
