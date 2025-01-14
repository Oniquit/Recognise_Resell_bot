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

load_dotenv() 

TOKEN=os.getenv('TOKEN')
BRICKOGNIZE_API_URL = "https://api.brickognize.com/predict/"


bot = telebot.TeleBot(TOKEN)

parsed_data = []
lego_details = {}

@bot.message_handler(commands=['start'])
def start(message):
    reset_session_data()
    bot.send_message(message.chat.id, "Здравствуйте! Пожалуйста, пришлите мне фотографию набора, минифигурки или детали LEGO, и я постараюсь идентифицировать его для вас. Желательно, чтобы фото было на однотонном фоне и хорошего качества.")

@bot.message_handler(commands=['restart'])
def restart(message):
    reset_session_data()
    bot.send_message(message.chat.id, "Перезапускаем бота...")
    start(message) 

def reset_session_data():
    global parsed_data, lego_details
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

 
        response_message = f"Найденный товар:\nНазвание: {name}\nID: {lego_id}\nURL: {url}\n\nХотите ли Вы найти данный товар на Авито или на Lekub.ru?"
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add('Авито', 'Lekub.ru')
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
                time.sleep(2)  # Wait before retrying
            else:
                print("Достигнуто максимальное количество повторных попыток. Не удалось подключиться к API.")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Запросить исключение при попытке {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retrying
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
        avito_data = search_avito(query)
        parsed_data.extend(avito_data)
        ask_for_format(message)
    elif message.text.lower() == 'lekub.ru':
        name = lego_details.get('name', '')
        lego_id = lego_details.get('id', '')
        query = f"{name} {lego_id}"
        bot.send_message(message.chat.id, f"Ищу: {query} на Lekub.ru...")
        lekub_data = search_lekub(query)
        parsed_data.extend(lekub_data)
        ask_for_format(message)
    else:
        bot.send_message(message.chat.id, "Некорректный выбор. Выберите из Авито и Lekub.ru")
        bot.register_next_step_handler(message, handle_resource_choice, lego_details)

def ask_for_format(message):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add('Вывести результаты в Telegram', 'Сохранить в формате JSON', 'Сохранить в формате CSV')
    bot.send_message(message.chat.id, "Как бы вы хотели получить данные?", reply_markup=markup)
    bot.register_next_step_handler(message, handle_save_format)


def search_avito(query: str):
    try:
        driver = Driver(uc=True)
        driver.uc_open_with_reconnect(f'https://www.avito.ru/moskva?q={query}', reconnect_time=4)
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
        return listings
    
    except Exception as e:
        print(f"Ошибка во время парсинга Авито: {e}")
        driver.quit()
        return []
    
def search_lekub(query: str):
    try:
        driver = Driver(uc=True)
        driver.uc_open_with_reconnect(f'https://lekub.ru/search/?keyword={query}', reconnect_time=4)
        driver.uc_gui_click_captcha()

        listings = []
        items = driver.find_elements(By.CSS_SELECTOR, '.pinfo')
        
        for item in items:
            name = item.find_element(By.CSS_SELECTOR, 'h2').text
            link = item.find_element(By.CSS_SELECTOR, "a").get_attribute('href')
            price = item.find_element(By.CSS_SELECTOR, "[itemprop='price']").get_attribute('content')
        
            listings.append({
                'name': name,
                'price': price,
                'url': link
            })
        
        driver.quit()
        return listings
    
    except Exception as e:
        print(f"Ошибка во время парсинга Lekub.ru: {e}")
        driver.quit()
        return []


def handle_save_format(message):
    if message.text.lower() == 'вывести результаты в telegram':
        for result in parsed_data:
            response_message = f"Название: {result['name']}\nОписание: {result['description']}\nЦена: {result['price']}\nURL: {result['url']}"
            bot.send_message(message.chat.id, response_message)
    elif message.text.lower() == 'сохранить в формате json':
        save_as_json(parsed_data, message)
    elif message.text.lower() == 'сохранить в формате csv':
        save_as_csv(parsed_data, message)

def save_as_json(data, message):
    json_filename = 'avito_data.json'
    with open(json_filename, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    

    with open(json_filename, 'rb') as file:
        bot.send_document(message.chat.id, file)

    os.remove(json_filename)

def save_as_csv(data, message):
    csv_filename = 'avito_data.csv'
    keys = data[0].keys()
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

    with open(csv_filename, 'rb') as file:
        bot.send_document(message.chat.id, file)
    
    os.remove(csv_filename)

bot.infinity_polling(timeout=10, long_polling_timeout = 5)
