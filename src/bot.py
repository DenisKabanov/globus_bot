#===============================================================================
# файл для запуска телеграм бота
#===============================================================================

import json
import os # для переменных окружения (токена бота)
import random # для случайного выбора
import numpy as np
import pandas as pd
from pyxdameraulevenshtein import damerau_levenshtein_distance # для подсчёта минимального числа изменений в первой строке, чтобы она стала идентичной второй
from dotenv import load_dotenv # для загрузки переменных окружения
from telegram import Update, KeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram.ext import MessageHandler, Filters
from telegram import ReplyKeyboardMarkup
# import logging # для логирования


load_dotenv() # загрузка переменных окружения
TOKEN = os.getenv("TOKEN") # берём токен бота из переменных окружения
DATA_PATH = os.getenv("DATA_PATH")
DB_PATH = os.getenv("DB_PATH")


db = pd.DataFrame()
if os.path.exists(f"{DB_PATH}/users.json"):
    db = pd.read_json(f"{DB_PATH}/users.json", lines=True)
else:
    db = pd.DataFrame(columns=["user_name", "chat_id", "current_country", "current_answer", "countries_history"])
    db.to_json(f"{DB_PATH}/users.json", orient='records', lines=True, force_ascii=False)


data = {}
for country_name in os.listdir(DATA_PATH):
    data[country_name] = {}
    data[country_name]["flag"] = f"{DATA_PATH}/{country_name}/flag.png"
    data[country_name]["map"] = f"{DATA_PATH}/{country_name}/map.png"
    data[country_name]["description"] = {}
    
    with open(f"{DATA_PATH}/{country_name}/description.txt", "r", encoding="utf-8") as f:
        for hint in ["Природа", "Достопримечательности", "Культура", "Язык", "Исторический факт", "Города"]:
            data[country_name]["description"][hint] = f.readline()[len(hint) + 2:]
            f.readline()
        
        data[country_name]["description"]["Общее описание"] = "".join(f.readlines(-1))


button1 = KeyboardButton("/start")
button2 = KeyboardButton("/help")
button3 = KeyboardButton("загадай")
button4 = KeyboardButton("расскажи о стране")

kb_basic = ReplyKeyboardMarkup(
    keyboard=[
        [button1, button2],
        [button3, button4]
    ],
    resize_keyboard=True  # Optional: Resizes the keyboard to fit the screen
)

button_help1 = KeyboardButton("подскажи природу")
button_help2 = KeyboardButton("подскажи достопримечательность")
button_help3 = KeyboardButton("подскажи культуру")
button_help4 = KeyboardButton("подскажи язык")
button_help5 = KeyboardButton("подскажи исторический факт")
button_help6 = KeyboardButton("подскажи города")
button_help7 = KeyboardButton("подскажи часть названия")
button_help8 = KeyboardButton("подскажи буквы")

kb_help = ReplyKeyboardMarkup(
    keyboard=[
        [button_help1, button_help2],
        [button_help3, button_help4],
        [button_help5, button_help6],
        [button_help7, button_help8]
    ],
    resize_keyboard=True  # Optional: Resizes the keyboard to fit the screen
)


def save_db(db: pd.DataFrame) -> None:
    with open(f"{DB_PATH}/users.json", mode='w', encoding='utf-8') as file:
        db.to_json(file, orient='records', lines=True, force_ascii=False)


# Функция-обработчик команды /start
def start(update: Update, context: CallbackContext) -> None:
    global db
    chat_id = update.message.chat.id
    user_name = update.message.chat.first_name

    if (chat_id not in db["chat_id"].values):
        new_user = pd.DataFrame({"user_name": [user_name], "chat_id": [chat_id], "current_country": [None], "current_answer": [None], "countries_history": [[]]})
        db = pd.concat([db, new_user], ignore_index=True)
        save_db(db)

    update.message.reply_text(f"Привет, {user_name}! Начнем викторину? \nВыберите команду:", reply_markup=kb_basic)


def help(update: Update, context: CallbackContext):
   update.message.reply_text(f"Поддерживаемые сообщения:\n\
1) '<b>загадай</b>' — для загадывания страны\n\
2) '<b>подскажи *</b>', где * это слово из (природу, достопримечательности, культуру, язык, исторический факт, города, часть названия) — для подсказки\n\
3) '<b>сдаюсь</b>' — чтобы признать поражение и узнать, какой стране принадлежит флаг\n\
4) '<b>расскажи о стране *</b>', где * это название страны — чтобы бот мог поведать информацию о ней, без загадывания (для произвольной страны вместо * нужно написать 'любой')\n\
5) ну и конечно же само <b>название страны</b>, если она была загадана", parse_mode='HTML') # отправляем сообщение (text) в чат (chat_id) 


def repeat(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(update.message.text)


def send_flag(update: Update, context: CallbackContext) -> None:
    global db
    chat_id = update.message.chat.id

    country_number = random.choices(range(len(data)), k=1)[0]
    country_name = list(data.keys())[country_number]
    
    flag_path = data[country_name]['flag']
    context.bot.send_photo(chat_id=chat_id, photo=open(flag_path, 'rb'), caption=f"В названии вашей страны присутствуют {len(country_name)} символов!", reply_markup=kb_help)

    db.loc[db["chat_id"] == chat_id, "current_country"] = country_name

    current_answer = ["*" for i in range(len(country_name))]
    for idx, char in enumerate(country_name):
        if char in [" ", "—", "-", "'"]:
            current_answer[idx] = char
    db.loc[db["chat_id"] == chat_id, "current_answer"] = "".join(current_answer)

    save_db(db)


def answer_flag(update: Update, context: CallbackContext) -> None:
    global db
    chat_id = update.message.chat.id

    answer_given = update.message.text
    answer_expected = db.loc[db["chat_id"] == chat_id, "current_country"].iloc[0]

    if answer_expected is None:
        update.message.reply_text(f"Вы ещё не загадали страну! \nВыберите следующую команду:", reply_markup=kb_basic)
        return

    if answer_given.lower() == answer_expected.lower():
        map_path = data[answer_expected]["map"]
        description = data[answer_expected]["description"]["Общее описание"]
        context.bot.send_photo(chat_id=chat_id, photo=open(map_path, 'rb'), caption=f"Поздравляю, страна {answer_expected} угадана! \n{description}")
        update.message.reply_text(f"Выберите следующую команду:", reply_markup=kb_basic)

        db.loc[db["chat_id"] == chat_id, "current_country"] = None
        db.loc[db["chat_id"] == chat_id, "current_answer"] = None
        db.loc[db["chat_id"] == chat_id, "countries_history"].iloc[0].append(answer_expected)
    else:
        correct_letters = 0 # число совпавших букв
        current_answer = list(db.loc[db["chat_id"] == chat_id, "current_answer"].iloc[0])

        for i in range(min(len(answer_given), len(answer_expected))): # идём по минимальной длине
            if answer_given[i].lower() == answer_expected[i].lower(): # сравниваем буквы на позициях
                correct_letters += 1 # увеличиваем число совпадений
                current_answer[i] = answer_given[i]
        current_answer = "".join(current_answer)
        
        db.loc[db["chat_id"] == chat_id, "current_answer"] = current_answer

        update.message.reply_text(f"Совпадений {correct_letters}: {current_answer}. \nПопытайся ещё раз!", reply_markup=kb_help)
    save_db(db)

def hint(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    hint_type = update.message.text[9:]

    country_name = db.loc[db["chat_id"] == chat_id, "current_country"].iloc[0]
    name_len = len(country_name)

    if damerau_levenshtein_distance(hint_type, "природу") <= 2:
        hint = data[country_name]['description']['Природа']
    elif damerau_levenshtein_distance(hint_type, "достопримечательность") <= 2:
        hint = data[country_name]['description']['Достопримечательности']
    elif damerau_levenshtein_distance(hint_type, "культуру") <= 2:
        hint = data[country_name]['description']['Культура']
    elif damerau_levenshtein_distance(hint_type, "язык") <= 2:
        hint = data[country_name]['description']['Язык']
    elif damerau_levenshtein_distance(hint_type, "исторический факт") <= 2:
        hint = data[country_name]['description']['Исторический факт']
    elif damerau_levenshtein_distance(hint_type, "города") <= 2:
        hint = data[country_name]['description']['Города']
    elif damerau_levenshtein_distance(hint_type, "часть названия") <= 2:
        start_idx, end_idx = sorted(random.sample(range(name_len), k=2)) # с какой по какую буквы подсказываем
        hint = "" # для подсказки части слова
        for i in range(name_len): # идём по числу букв в загаданном названии
            if start_idx <= i <= end_idx: # если буква в нужном интервале
                hint += country_name[i] # добавляем её саму
            else: # иначе
                hint += "*" # зашифровываем букву
    elif damerau_levenshtein_distance(hint_type, "буквы") <= 2:
        idx_to_show = sorted(random.sample(range(name_len), k=int(name_len/3))) # с какой по какую буквы подсказываем
        hint = "" # для подсказки части слова
        for i in range(name_len): # идём по числу букв в загаданном названии
            if (i in idx_to_show) or (country_name[i] in [" ", "—", "-", "'"]): # если буква в нужном интервале или является специальным символом
                hint += country_name[i] # добавляем её саму
            else: # иначе
                hint += "*" # зашифровываем букву

    update.message.reply_text(hint, reply_markup=kb_help)


def tell_about(update: Update, context: CallbackContext) -> None:
    print(update)
    print(context)
    #country_name = list(data.keys())[country_number]
    
    #flag_path = data[country_name]['flag']
    
    #chat_id = update.message.chat.id
    
    #context.bot.send_photo(chat_id=chat_id, photo=open(flag_path, 'rb'))


# def error(update: Update, context: CallbackContext) -> None:
#     logger.warning(f'Update {update} caused error {context.error}')


def main():
    updater = Updater(TOKEN) # API для взаимодействия с ботом

    dispatcher = updater.dispatcher # получение диспетчера для регистрации обработчиков

    # Регистрация обработчика команд
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))
    # dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, repeat))
    dispatcher.add_handler(MessageHandler(Filters.regex(r"[З|з]агадай"), send_flag))
    dispatcher.add_handler(MessageHandler(Filters.regex(r"[П|п]одскажи .*"), hint))
    dispatcher.add_handler(MessageHandler(Filters.regex(r"[Р|р]асскажи о"), tell_about))
    dispatcher.add_handler(MessageHandler(Filters.text, answer_flag)) 
    
    # dispatcher.add_error_handler(error)

    updater.start_polling() # Запуск бота

    # Ожидание завершения работы
    updater.idle()

if __name__ == '__main__':
    main()