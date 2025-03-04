#===============================================================================
# файл для запуска телеграм бота
#===============================================================================

import os # для переменных окружения (токена бота)
import random # для случайного выбора
import sqlite3 # для работы с базами данных
from dotenv import load_dotenv # для загрузки переменных окружения
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram.ext import MessageHandler, Filters
from telegram import ReplyKeyboardMarkup
import logging # для логирования

load_dotenv() # загрузка переменных окружения
token = os.getenv('TOKEN') # берём токен бота из переменных окружения

logging.basicConfig(format='%(asctime)s – %(name)s – %(levelname)s – %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# Функция-обработчик команды /start
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Привет! Я ваш бот.')
    keyboard = [['/start', '/help'], ['/repeat']]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    update.message.reply_text('Выберите команду:', reply_markup=reply_markup)


def help(update: Update, context: CallbackContext):
   update.message.reply_text(f"Поддерживаемые сообщения:\n\
1) '<b>загадай</b>' — для загадывания страны\n\
2) '<b>подскажи *</b>', где * это слово из (природу, достопримечательности, культуру, язык, исторический факт, города, часть названия) — для подсказки\n\
3) '<b>сдаюсь</b>' — чтобы признать поражение и узнать, какой стране принадлежит флаг\n\
4) '<b>расскажи о *</b>', где * это название страны — чтобы бот мог поведать информацию о ней, без загадывания (для произвольной страны вместо * нужно написать 'любой')\n\
5) ну и конечно же само <b>название страны</b>, если она была загадана", parse_mode='HTML') # отправляем сообщение (text) в чат (chat_id) 


def repeat(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(update.message.text)


def error(update: Update, context: CallbackContext) -> None:
    logger.warning(f'Update {update} caused error {context.error}')

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
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, repeat))
    dispatcher.add_error_handler(error)

    updater.start_polling() # Запуск бота

    # Ожидание завершения работы
    updater.idle()

if __name__ == '__main__':
    main()