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
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
# import logging # для логирования


load_dotenv() # загрузка переменных окружения
TOKEN = os.getenv("TOKEN") # берём токен бота из переменных окружения
DATA_PATH = os.getenv("DATA_PATH")
DB_PATH = os.getenv("DB_PATH")
EXTRA_PATH = os.getenv("EXTRA_PATH")


db = pd.DataFrame()
if os.path.exists(f"{DB_PATH}/users.json"):
    db = pd.read_json(f"{DB_PATH}/users.json", lines=True)
else:
    variables = {
        "user_name": str(),
        "chat_id": int(),
        "current_country": str(),
        "current_answer": str(),
        "countries_history": list(),
        "score_total" : int(),
        "score_best" : int(),
        "score_countries" : dict()
    }

    db = pd.DataFrame(columns=variables, index=[])
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
countries_all = set(data.keys()) # set с названиями всех стран


button1 = KeyboardButton("загадай")
button2 = KeyboardButton("расскажи о стране")
kb_basic = ReplyKeyboardMarkup(
    keyboard=[
        [button1, button2]
    ],
    resize_keyboard=True  # Optional: Resizes the keyboard to fit the screen
)


button_help1 = KeyboardButton("подскажи природу (-10 балл)")
button_help2 = KeyboardButton("подскажи достопримечательность (-10 балл)")
button_help3 = KeyboardButton("подскажи культуру (-10 балл)")
button_help4 = KeyboardButton("подскажи язык (-10 балл)")
button_help5 = KeyboardButton("подскажи исторический факт (-10 балл)")
button_help6 = KeyboardButton("подскажи города (-10 балл)")
button_help7 = KeyboardButton("подскажи часть названия (-40 балла)")
button_help8 = KeyboardButton("подскажи буквы (-20 балла)")
button_surrender = KeyboardButton("сдаюсь")
kb_help = ReplyKeyboardMarkup(
    keyboard=[
        [button_help1, button_help2],
        [button_help3, button_help4],
        [button_help5, button_help6],
        [button_help7, button_help8],
        [button_surrender]
    ],
    resize_keyboard=True  # Optional: Resizes the keyboard to fit the screen
)


button_reset = KeyboardButton(text="очистить историю")
kb_reset = ReplyKeyboardMarkup(
    keyboard=[
        [button_reset]
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
        new_user = pd.DataFrame({"user_name": [user_name], "chat_id": [chat_id], "current_country": [""], "current_answer": [""],
                                 "countries_history": [[]], "score_total": [0], "score_best": [0], "score_countries": [{}]})
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


def clear_history(update: Update, context: CallbackContext):
    global db
    chat_id = update.message.chat.id

    db.loc[db["chat_id"] == chat_id, "current_country"] = ""
    db.loc[db["chat_id"] == chat_id, "current_answer"] = ""
    db.loc[db["chat_id"] == chat_id, "countries_history"].iloc[0].clear()
    db.loc[db["chat_id"] == chat_id, "score_total"] = 0
    db.loc[db["chat_id"] == chat_id, "score_best"] = 0
    db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0].clear()
    
    save_db(db)

    update.message.reply_text(f"История взаимодействия с приложением очищена!", reply_markup=kb_basic)


def send_flag(update: Update, context: CallbackContext) -> None:
    global db
    chat_id = update.message.chat.id

    countries_history = set(db.loc[db["chat_id"] == chat_id, "countries_history"].iloc[0])
    if len(countries_history) == len(countries_all):
        gif_animation = open(f"{EXTRA_PATH}/win.gif", "rb")
        context.bot.send_animation(chat_id=chat_id, animation=gif_animation, caption=f"🎉Поздравляем, Вы отгадали все страны! Хотите начать новую викторину?🎉", reply_markup=kb_reset)
        return

    country_name = random.choices(list(countries_all - countries_history), k=1)[0]
    
    flag_path = data[country_name]["flag"]

    # update.message.reply_text(f"{country_name}") # DEBUG
    context.bot.send_photo(chat_id=chat_id, photo=open(flag_path, "rb"), caption=f"В названии вашей страны присутствуют {len(country_name)} символов!", reply_markup=kb_help)

    db.loc[db["chat_id"] == chat_id, "current_country"] = country_name
    db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0][country_name] = 100

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
    score_countries = db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0]
    # current_score = score_countries[answer_expected]
    current_country_score = score_countries[answer_expected]
    total_score = db.loc[db["chat_id"] == chat_id, "score_total"].iloc[0]
    best_score = db.loc[db["chat_id"] == chat_id, "best_score"].iloc[0]

    if answer_expected == "":
        update.message.reply_text(f"Вы ещё не загадали страну! \nВыберите следующую команду:", reply_markup=kb_basic)
        return
    
    # if answer_expected in countries_hint.keys():
    #     current_score = current_score - countries_hint[answer_expected]
            
    if (answer_given.lower() == answer_expected.lower()) or \
       ((answer_expected == "Китайская Народная Республика") and (answer_given.lower() == "китай")) or \
       ((answer_expected == "Корейская Народно-Демократическая Республика") and (answer_given.lower() == "кндр")) or \
       ((answer_expected == "Объединенные Арабские Эмираты") and (answer_given.lower() == "оаэ")) or \
       ((answer_expected == "Республика Корея") and (answer_given.lower() == "южная корея")) or \
       ((answer_expected == "Сахарская Арабская Демократическая Республика") and (answer_given.lower() == "садр")) or \
       ((answer_expected == "Соединенные Штаты Америки") and (answer_given.lower() == "сша")) or \
       ((answer_expected == "Турецкая Республика Северного Кипра") and (answer_given.lower() == "трск")) or \
       ((answer_expected == "Южно-Африканская Республика") and (answer_given.lower() == "юар")):
        map_path = data[answer_expected]["map"]
        description = data[answer_expected]["description"]["Общее описание"]

        new_total_score = total_score + max(0, current_country_score)
        db.loc[db["chat_id"] == chat_id, "score_total"] = new_total_score
        if new_total_score > best_score:
            db.loc[db["chat_id"] == chat_id, "score_best"] = new_total_score

        update.message.reply_text(f"Поздравляю, страна {answer_expected} угадана! За отгадывание страны вы получили {current_country_score}. Текущий счёт: {new_total_score}.")
        context.bot.send_photo(chat_id=chat_id, photo=open(map_path, "rb"), caption=f"{description}")
        update.message.reply_text(f"Выберите следующую команду:", reply_markup=kb_basic)

        db.loc[db["chat_id"] == chat_id, "current_country"] = ""
        db.loc[db["chat_id"] == chat_id, "current_answer"] = ""
        db.loc[db["chat_id"] == chat_id, "countries_history"].iloc[0].append(answer_expected)
        db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0].pop(answer_expected, None)
    else:
        db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0][answer_expected] -= 1
        
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


def surrender(update: Update, context: CallbackContext) -> None:
    global db
    chat_id = update.message.chat.id

    answer_expected = db.loc[db["chat_id"] == chat_id, "current_country"].iloc[0]

    if answer_expected == "":
        update.message.reply_text(f"Вы ещё не загадали страну! \nВыберите следующую команду:", reply_markup=kb_basic)
    else:
        map_path = data[answer_expected]["map"]
        description = data[answer_expected]["description"]["Общее описание"]
        context.bot.send_photo(chat_id=chat_id, photo=open(map_path, "rb"), caption=f"Вам была загадана страна {answer_expected}. \n{description}")
        update.message.reply_text(f"Выберите следующую команду:", reply_markup=kb_basic)

        db.loc[db["chat_id"] == chat_id, "current_country"] = ""
        db.loc[db["chat_id"] == chat_id, "current_answer"] = ""
        save_db(db)


def hint(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    hint_type = update.message.text[9:]

    country_name = db.loc[db["chat_id"] == chat_id, "current_country"].iloc[0]
    name_len = len(country_name)

    if damerau_levenshtein_distance(hint_type, "природу") <= 2:
        hint = data[country_name]["description"]["Природа"]
    elif damerau_levenshtein_distance(hint_type, "достопримечательность") <= 2:
        hint = data[country_name]["description"]["Достопримечательности"]
    elif damerau_levenshtein_distance(hint_type, "культуру") <= 2:
        hint = data[country_name]["description"]["Культура"]
    elif damerau_levenshtein_distance(hint_type, "язык") <= 2:
        hint = data[country_name]["description"]["Язык"]
    elif damerau_levenshtein_distance(hint_type, "исторический факт") <= 2:
        hint = data[country_name]["description"]["Исторический факт"]
    elif damerau_levenshtein_distance(hint_type, "города") <= 2:
        hint = data[country_name]["description"]["Города"]
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
    global db
    chat_id = update.message.chat.id

    country_name = update.message.text[17:].strip()
    countries_history = set(db.loc[db["chat_id"] == chat_id, "countries_history"].iloc[0])

    if (len(country_name) <= 2) or (damerau_levenshtein_distance(country_name, "любой") <= 2):
        country_name = random.choices(list(countries_all - countries_history), k=1)[0]
        flag_path = data[country_name]["flag"]
        map_path = data[country_name]["map"]
        description = data[country_name]["description"]["Общее описание"]
    else:
        dist_best = 3
        country_name_closest = ""
        for country in countries_all:
            dist = damerau_levenshtein_distance(country_name, country)
            if dist < dist_best:
                country_name_closest = country
                dist_best = dist

        if country_name_closest == "":
            update.message.reply_text(f"Введённая страна {country_name} не найдена.", reply_markup=kb_basic)
            return
        else:  
            flag_path = data[country_name_closest]["flag"]
            map_path = data[country_name_closest]["map"]
            description = data[country_name_closest]["description"]["Общее описание"]
    
    media = [
        InputMediaPhoto(open(flag_path, "rb"), caption=description),
        InputMediaPhoto(open(map_path, "rb"))
    ]

    update.message.reply_media_group(media)
    update.message.reply_text(f"Выберите следующую команду:", reply_markup=kb_basic)

# def error(update: Update, context: CallbackContext) -> None:
#     logger.warning(f'Update {update} caused error {context.error}')


def main():
    updater = Updater(TOKEN) # API для взаимодействия с ботом

    dispatcher = updater.dispatcher # получение диспетчера для регистрации обработчиков

    # Регистрация обработчика команд
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("clear_history", clear_history))
    dispatcher.add_handler(MessageHandler(Filters.regex(r"[О|о]чистить историю"), clear_history))
    # dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, repeat))
    dispatcher.add_handler(MessageHandler(Filters.regex(r"[З|з]агадай"), send_flag))
    dispatcher.add_handler(MessageHandler(Filters.regex(r"[П|п]одскажи .*"), hint))
    dispatcher.add_handler(MessageHandler(Filters.regex(r"[С|с]даюсь"), surrender))
    dispatcher.add_handler(MessageHandler(Filters.regex(r"[Р|р]асскажи о"), tell_about))
    dispatcher.add_handler(MessageHandler(Filters.text, answer_flag)) 
    
    # dispatcher.add_error_handler(error)

    updater.start_polling() # Запуск бота

    # Ожидание завершения работы
    updater.idle()

if __name__ == '__main__':
    main()