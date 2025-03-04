#===============================================================================
# файл для запуска телеграм бота
#===============================================================================

import json
import os # для переменных окружения (токена бота)
import random # для случайного выбора
import sqlite3 # для работы с базами данных
import numpy as np
from dotenv import load_dotenv # для загрузки переменных окружения
from telebot import TeleBot
from telegram import Update, KeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram.ext import MessageHandler, Filters
from telegram import ReplyKeyboardMarkup
#import logging # для логирования


load_dotenv() # загрузка переменных окружения
token = os.getenv('TOKEN') # берём токен бота из переменных окружения
data_path = os.getenv('DATA_PATH')
bot = TeleBot(token=token) 

data = {}

for country_name in os.listdir(data_path):
    
    data[country_name] = {}
    data[country_name]["flag"] = f"{data_path}/{country_name}/flag.png"
    data[country_name]["map"] = f"{data_path}/{country_name}/map.png"

    data[country_name]["description"] = {}
    
    with open(f"{data_path}/{country_name}/description.txt", "r", encoding="utf-8") as f:
        
        for hint in ["Природа", "Достопримечательности", "Культура", "Язык", "Исторический факт", "Города"]:
            
            data[country_name]["description"][hint] = f.readline()[len(hint) + 2:]
            f.readline()
        
        data[country_name]["description"]["Общее описание"] = f.readline(-1)    


# Функция-обработчик команды /start
def start(update: Update, context: CallbackContext) -> None:
    
    user_id = update.message.chat.id
    user_name = update.message.chat.first_name
    
    button1 = KeyboardButton("/start")
    button2 = KeyboardButton("/help")
    button3 = KeyboardButton("загадай")
    button4 = KeyboardButton("расскажи о")

    kb_commands = ReplyKeyboardMarkup(
        keyboard=[
            [button1, button2],
            [button3, button4]
        ],
        resize_keyboard=True  # Optional: Resizes the keyboard to fit the screen
    )

    update.message.reply_text(f"Привет, {user_name}! Начнем викторину? \nВыберите команду:", reply_markup=kb_commands)


def help(update: Update, context: CallbackContext):
   update.message.reply_text(f"Поддерживаемые сообщения:\n\
1) '<b>загадай</b>' — для загадывания страны\n\
2) '<b>подскажи *</b>', где * это слово из (природу, достопримечательности, культуру, язык, исторический факт, города, часть названия) — для подсказки\n\
3) '<b>сдаюсь</b>' — чтобы признать поражение и узнать, какой стране принадлежит флаг\n\
4) '<b>расскажи о *</b>', где * это название страны — чтобы бот мог поведать информацию о ней, без загадывания (для произвольной страны вместо * нужно написать 'любой')\n\
5) ну и конечно же само <b>название страны</b>, если она была загадана", parse_mode='HTML') # отправляем сообщение (text) в чат (chat_id) 


def repeat(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(update.message.text)
    
def send_flag(update: Update, context: CallbackContext) -> None:
    
    country_number = random.choices(np.arange(len(data)), k=1)[0]
    
    country_name = list(data.keys())[country_number]
    
    flag_path = data[country_name]['flag']
    
    chat_id = update.message.chat.id
    
    context.bot.send_photo(chat_id=chat_id, photo=open(flag_path, 'rb'))
    
def tell_about(update: Update, context: CallbackContext) -> None:
    
    print(update)
    print(context)
    #country_name = list(data.keys())[country_number]
    
    #flag_path = data[country_name]['flag']
    
    #chat_id = update.message.chat.id
    
    #context.bot.send_photo(chat_id=chat_id, photo=open(flag_path, 'rb'))


#def error(update: Update, context: CallbackContext) -> None:
    #logger.warning(f'Update {update} caused error {context.error}')

def init_db():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id, username):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO users (id, username) VALUES (?, ?)''', (user_id, username))
    conn.commit()
    conn.close()


def main():
    updater = Updater(token) # API для взаимодействия с ботом

    dispatcher = updater.dispatcher # получение диспетчера для регистрации обработчиков

    # Регистрация обработчика команд
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))
    #dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, repeat))
    dispatcher.add_handler(MessageHandler(Filters.regex(r"загадай"), send_flag))
    dispatcher.add_handler(MessageHandler(Filters.regex(r"расскажи о"), tell_about))  
    
    #dispatcher.add_error_handler(error)

    updater.start_polling() # Запуск бота

    # Ожидание завершения работы
    updater.idle()

if __name__ == '__main__':
    main()