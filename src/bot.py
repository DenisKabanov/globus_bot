#===============================================================================
# файл для запуска телеграм бота
#===============================================================================

import os # для переменных окружения (токена бота)
import re # для регулярных выражений
import random # для случайного выбора
import pandas as pd # для работы с базой данных
from dotenv import load_dotenv # для загрузки переменных окружения
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler
from pyxdameraulevenshtein import damerau_levenshtein_distance # для подсчёта минимального числа изменений в первой строке, чтобы она стала идентичной второй
# import logging # для логирования


load_dotenv() # загрузка переменных окружения
TOKEN = os.getenv("TOKEN") # берём токен бота из переменных окружения
DATA_PATH = os.getenv("DATA_PATH")
DB_PATH = os.getenv("DB_PATH")
EXTRA_PATH = os.getenv("EXTRA_PATH")
LEADERBOARD_SIZE = int(os.getenv("LEADERBOARD_SIZE"))


db = pd.DataFrame()
if os.path.exists(f"{DB_PATH}/users.json") and os.path.getsize(f"{DB_PATH}/users.json") > 1: # проверка, что файл существует и в нём что-нибудь записано (минимальный размер файла - 1 байт, если он пуст)
    db = pd.read_json(f"{DB_PATH}/users.json", lines=True)
else:
    variables = {
        "user_name": str(),
        "chat_id": int(),
        "current_country": str(),
        "current_answer": str(),
        "countries_history": list(),
        "score_total": int(),
        "score_best": int(),
        "score_countries": dict(),
        "hint_countries": dict(),
        "potw": str()
    }

    db = pd.DataFrame(columns=variables, index=[])
    db.to_json(f"{DB_PATH}/users.json", orient='records', lines=True, force_ascii=False)


data = {}
countries_potw = {"all": set()} # "all" — под все страны сразу
for country_name in os.listdir(DATA_PATH):
    data[country_name] = {}
    data[country_name]["flag"] = f"{DATA_PATH}/{country_name}/flag.png"
    data[country_name]["map"] = f"{DATA_PATH}/{country_name}/map.png"
    data[country_name]["description"] = {}
    
    with open(f"{DATA_PATH}/{country_name}/description.txt", "r", encoding="utf-8") as f:
        potw = f.readline()[13:-1]
        f.readline()
        for potw_ in potw.split("|"):
            if potw_ not in countries_potw.keys():
                countries_potw[potw_] = set([country_name])
            else:
                countries_potw[potw_].add(country_name)
        countries_potw["all"].add(country_name)
        
        for hint in ["Природа", "Достопримечательности", "Культура", "Язык", "Исторический факт", "Города"]:
            data[country_name]["description"][hint] = f.readline()[len(hint) + 2:]
            f.readline()
        
        data[country_name]["description"]["Общее описание"] = "".join(f.readlines(-1))


button1 = KeyboardButton("загадай")
button2 = KeyboardButton("расскажи о стране")
button3 = KeyboardButton("выведи таблицу лидеров")
button4 = KeyboardButton("выбрать часть света")
kb_basic = ReplyKeyboardMarkup(
    keyboard=[
        [button1, button2],
        [button3, button4]
    ],
    resize_keyboard=True  # Optional: Resizes the keyboard to fit the screen
)


button_potw1 = InlineKeyboardButton("Америка", callback_data="Америка")
button_potw2 = InlineKeyboardButton("Европа", callback_data="Европа")
button_potw3 = InlineKeyboardButton("Азия", callback_data="Азия")
button_potw4 = InlineKeyboardButton("Африка", callback_data="Африка")
button_potw5 = InlineKeyboardButton("Австралия и Океания", callback_data="Австралия и Океания")
button_potw6 = InlineKeyboardButton("все страны сразу", callback_data="all")
kb_potw = InlineKeyboardMarkup(
    inline_keyboard=[
        [button_potw1, button_potw2],
        [button_potw3, button_potw4],
        [button_potw5, button_potw6]
    ],
    resize_keyboard=True  # Optional: Resizes the keyboard to fit the screen
)


button_help1 = KeyboardButton("подскажи природу (-10 баллов)")
button_help2 = KeyboardButton("подскажи культуру (-5 баллов)")
button_help3 = KeyboardButton("подскажи язык (-5 баллов)")
button_help4 = KeyboardButton("подскажи города (-20 баллов)")
button_help5 = KeyboardButton("подскажи часть названия (-40 баллов)")
button_help6 = KeyboardButton("подскажи буквы (-20 баллов)")
button_help7 = KeyboardButton("подскажи достопримечательность (-15 баллов)")
button_help8 = KeyboardButton("подскажи исторический факт (-10 баллов)")
button_surrender = KeyboardButton("сдаюсь")
kb_help = ReplyKeyboardMarkup(
    keyboard=[
        [button_help1, button_help2],
        [button_help3, button_help4],
        [button_help5, button_help6],
        [button_help7], 
        [button_help8],
        [button_surrender]
    ],
    resize_keyboard=True  # Optional: Resizes the keyboard to fit the screen
)


button_reset = KeyboardButton("очистить историю")
button_change_potw = KeyboardButton("выбрать часть света")
kb_reset = ReplyKeyboardMarkup(
    keyboard=[
        [button_reset],
        [button_change_potw]
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
    if update.message.chat.last_name is not None:
        user_name += f" {update.message.chat.last_name}"

    if (chat_id not in db["chat_id"].values):
        new_user = pd.DataFrame({"user_name": [user_name], "chat_id": [chat_id], "current_country": [""], "current_answer": [""], "countries_history": [[]], 
                                 "score_total": [0], "score_best": [0], "score_countries": [{}], "hint_countries": [{}], "potw": ["all"]})
        db = pd.concat([db, new_user], ignore_index=True)
        save_db(db)

    update.message.reply_text(f"Привет, {user_name}! Начнём викторину? \nВыберите команду:", reply_markup=kb_basic)


def help(update: Update, context: CallbackContext):
   update.message.reply_text(f"Поддерживаемые сообщения:\n\
1) '<b>загадай</b>' — для загадывания страны\n\
2) '<b>подскажи *</b>', где * это слово из (природу, достопримечательности, культуру, язык, исторический факт, города, часть названия, буквы) — для подсказки\n\
3) '<b>сдаюсь</b>' — чтобы признать поражение и узнать, какой стране принадлежит флаг\n\
4) '<b>расскажи о стране *</b>', где * это название страны — чтобы бот мог поведать информацию о ней, без загадывания (для произвольной страны вместо * нужно написать 'любой')\n\
5) '<b>выведи таблицу лидеров</b>' — чтобы посмотреть рейтинг лучших игроков\n\
6) '<b>выбрать часть света</b>' — для загадывания стран только из определённой части света, если ничего не выбрано, то загадываются все страны\n\
7) ну и конечно же само <b>название страны</b>, если она была загадана", parse_mode="HTML") # отправляем сообщение (text) в чат (chat_id) 


def clear_history(update: Update, context: CallbackContext) -> None:
    global db
    chat_id = update.message.chat.id

    db.loc[db["chat_id"] == chat_id, "current_country"] = ""
    db.loc[db["chat_id"] == chat_id, "current_answer"] = ""
    db.loc[db["chat_id"] == chat_id, "countries_history"].iloc[0].clear()
    db.loc[db["chat_id"] == chat_id, "score_total"] = 0
    db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0].clear()
    db.loc[db["chat_id"] == chat_id, "hint_countries"].iloc[0].clear()
    db.loc[db["chat_id"] == chat_id, "potw"] = "all"
    
    save_db(db)

    update.message.reply_text(f"История взаимодействия с приложением очищена!", reply_markup=kb_basic)


def choose_potw(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    countries_history = set(db.loc[db["chat_id"] == chat_id, "countries_history"].iloc[0])

    context.bot.send_photo(chat_id=chat_id, photo=open(f"{EXTRA_PATH}/zones.png", "rb"), caption=f"Выберите часть света из представленных:\n\
- <b>Америка</b> — {len(countries_potw['Америка'] - countries_history)} неотгаданных стран\n\
- <b>Европа</b> — {len(countries_potw['Европа'] - countries_history)} неотгаданных стран\n\
- <b>Азия</b> — {len(countries_potw['Азия'] - countries_history)} неотгаданных стран\n\
- <b>Африка</b> — {len(countries_potw['Африка'] - countries_history)} неотгаданных стран\n\
- <b>Австралия и Океания</b> — {len(countries_potw['Австралия и Океания'] - countries_history)} неотгаданных стран\n\
- <b>все страны сразу</b> — {len(countries_potw['all'] - countries_history)}", parse_mode="HTML", reply_markup=kb_potw)


def choose_potw_(update: Update, context: CallbackContext) -> None:
    global db
    chat_id = update.callback_query.message.chat.id

    query = update.callback_query
    query.answer()
    choice = query.data
    db.loc[db["chat_id"] == chat_id, "potw"] = choice
    save_db(db)

    if choice != "all":
        update.callback_query.message.reply_text(f"Вами выбрана {choice}, последующие страны будут загадываться из неё!", reply_markup=kb_basic)
    else:
        update.callback_query.message.reply_text(f"Вами выбраны все страны сразу, удачи!", reply_markup=kb_basic)


def send_flag(update: Update, context: CallbackContext) -> None:
    global db
    chat_id = update.message.chat.id
    total_score = db.loc[db["chat_id"] == chat_id, "score_total"].iloc[0]
    potw = db.loc[db["chat_id"] == chat_id, "potw"].iloc[0]

    countries_history = set(db.loc[db["chat_id"] == chat_id, "countries_history"].iloc[0])
    if len(countries_history) == len(countries_potw["all"]):
        gif_animation = open(f"{EXTRA_PATH}/win.gif", "rb")
        context.bot.send_animation(chat_id=chat_id, animation=gif_animation, caption=f"🎉Поздравляем, Вы отгадали все страны! Общее количество заработанных баллов: {total_score}. Хотите начать новую викторину?🎉", reply_markup=kb_reset)
        return
    elif len(countries_potw[potw] - countries_history) == 0:
        gif_animation = open(f"{EXTRA_PATH}/win_potw.gif", "rb")
        context.bot.send_animation(chat_id=chat_id, animation=gif_animation, caption=f"🎉Поздравляем, Вы отгадали все страны! Общее количество заработанных баллов: {total_score}. Хотите начать новую викторину?🎉", reply_markup=kb_reset)
        return

    country_name = random.choices(list(countries_potw[potw] - countries_history), k=1)[0]
    
    flag_path = data[country_name]["flag"]

    # update.message.reply_text(f"{country_name}") # DEBUG

    db.loc[db["chat_id"] == chat_id, "current_country"] = country_name
    if country_name not in db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0]: # добавляем столбец с текущим счётом для загаданной страны
        db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0][country_name] = 100
    current_country_score = db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0][country_name]

    if country_name not in db.loc[db["chat_id"] == chat_id, "hint_countries"].iloc[0]: # добавляем столбец с использованными подсказками
        db.loc[db["chat_id"] == chat_id, "hint_countries"].iloc[0][country_name] = []

    current_answer = ["*" for i in range(len(country_name))]
    for idx, char in enumerate(country_name):
        if char in [" ", "—", "-", "'"]:
            current_answer[idx] = char
    db.loc[db["chat_id"] == chat_id, "current_answer"] = "".join(current_answer)

    context.bot.send_photo(chat_id=chat_id, photo=open(flag_path, "rb"), caption=f"В названии загаданной страны присутствует {len(country_name)} символов! За её отгадывание вы можете получить баллов: {current_country_score}.", reply_markup=kb_help)

    save_db(db)

def answer_flag(update: Update, context: CallbackContext) -> None:
    global db
    chat_id = update.message.chat.id

    answer_given = update.message.text
    answer_expected = db.loc[db["chat_id"] == chat_id, "current_country"].iloc[0]
    if answer_expected == "":
        update.message.reply_text(f"Вы ещё не загадали страну! \nВыберите следующую команду:", reply_markup=kb_basic)
        return
    
    score_countries = db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0]
    total_score = db.loc[db["chat_id"] == chat_id, "score_total"].iloc[0]
    best_score = db.loc[db["chat_id"] == chat_id, "score_best"].iloc[0]
    current_country_score = score_countries[answer_expected]
            
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
        
        current_country_score = max(0, current_country_score)
        new_total_score = total_score + current_country_score
        db.loc[db["chat_id"] == chat_id, "score_total"] = new_total_score
        if new_total_score > best_score:
            db.loc[db["chat_id"] == chat_id, "score_best"] = new_total_score

        update.message.reply_text(f"Поздравляю, страна {answer_expected} угадана! \nКоличество заработанных баллов: {current_country_score}. \nТекущий счёт: {new_total_score}.")
        context.bot.send_photo(chat_id=chat_id, photo=open(map_path, "rb"), caption=f"{description}")
        update.message.reply_text(f"Выберите следующую команду:", reply_markup=kb_basic)

        db.loc[db["chat_id"] == chat_id, "current_country"] = ""
        db.loc[db["chat_id"] == chat_id, "current_answer"] = ""
        db.loc[db["chat_id"] == chat_id, "countries_history"].iloc[0].append(answer_expected)
        db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0].pop(answer_expected, None)
        db.loc[db["chat_id"] == chat_id, "hint_countries"].iloc[0].pop(answer_expected, None)
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
        db.loc[db["chat_id"] == chat_id, "countries_history"].iloc[0].append(answer_expected)
        db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0].pop(answer_expected, None)
        db.loc[db["chat_id"] == chat_id, "hint_countries"].iloc[0].pop(answer_expected, None)
        
        save_db(db)


def hint(update: Update, context: CallbackContext) -> None:
    global db
    chat_id = update.message.chat.id
    hint_type = re.findall("[П|п]одскажи (.*?)(?= \(|$)", update.message.text)
    country_name = db.loc[db["chat_id"] == chat_id, "current_country"].iloc[0]
    name_len = len(country_name)

    if country_name == "":
        update.message.reply_text(f"Вы ещё не загадали страну! \nВыберите следующую команду:", reply_markup=kb_basic)
        return
    
    if len(hint_type) == 0:
        update.message.reply_text(f"Введите корректную подсказку:", reply_markup=kb_help)
        return
    hint_type = hint_type[0]
    used_hints = db.loc[db["chat_id"] == chat_id, "hint_countries"].iloc[0][country_name] # вернёт list

    # проверяем, использовали ли мы аналогичную подсказку раньше
    modifier = 1
    for hint in used_hints:
        if damerau_levenshtein_distance(hint_type, hint) <= 2:
            modifier = 0
    
    if damerau_levenshtein_distance(hint_type, "природу") <= 2:
        hint = data[country_name]["description"]["Природа"]
        db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0][country_name] -= 10 * modifier
    elif damerau_levenshtein_distance(hint_type, "достопримечательность") <= 2:
        hint = data[country_name]["description"]["Достопримечательности"]
        db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0][country_name] -= 15 * modifier
    elif damerau_levenshtein_distance(hint_type, "культуру") <= 2:
        hint = data[country_name]["description"]["Культура"]
        db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0][country_name] -= 5 * modifier
    elif damerau_levenshtein_distance(hint_type, "язык") <= 2:
        hint = data[country_name]["description"]["Язык"]
        db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0][country_name] -= 5 * modifier
    elif damerau_levenshtein_distance(hint_type, "исторический факт") <= 2:
        hint = data[country_name]["description"]["Исторический факт"]
        db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0][country_name] -= 10 * modifier
    elif damerau_levenshtein_distance(hint_type, "города") <= 2:
        hint = data[country_name]["description"]["Города"]
        db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0][country_name] -= 20 * modifier
    elif damerau_levenshtein_distance(hint_type, "часть названия") <= 2:
        db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0][country_name] -= 40
        start_idx, end_idx = sorted(random.sample(range(name_len), k=2)) # с какой по какую буквы подсказываем
        hint = "" # для подсказки части слова
        for i in range(name_len): # идём по числу букв в загаданном названии
            if start_idx <= i <= end_idx: # если буква в нужном интервале
                hint += country_name[i] # добавляем её саму
            else: # иначе
                hint += "*" # зашифровываем букву
    elif damerau_levenshtein_distance(hint_type, "буквы") <= 2:
        db.loc[db["chat_id"] == chat_id, "score_countries"].iloc[0][country_name] -= 20
        idx_to_show = sorted(random.sample(range(name_len), k=int(name_len/3))) # с какой по какую буквы подсказываем
        hint = "" # для подсказки части слова
        for i in range(name_len): # идём по числу букв в загаданном названии
            if (i in idx_to_show) or (country_name[i] in [" ", "—", "-", "'"]): # если буква в нужном интервале или является специальным символом
                hint += country_name[i] # добавляем её саму
            else: # иначе
                hint += "*" # зашифровываем букву
    else:
        update.message.reply_text(f"Введённой подсказки {hint_type} нет, введите корректную подсказку.", reply_markup=kb_help)
        return

    if hint_type not in used_hints: # сохраняем запись о том, что дали hint_type подсказку для страны country_name, если раньше её не запрашивали
        used_hints.append(hint_type)
    save_db(db)

    update.message.reply_text(hint, reply_markup=kb_help)


def tell_about(update: Update, context: CallbackContext) -> None:
    global db
    chat_id = update.message.chat.id

    country_name = update.message.text[17:].strip()
    countries_history = set(db.loc[db["chat_id"] == chat_id, "countries_history"].iloc[0])

    if (len(country_name) <= 2) or (damerau_levenshtein_distance(country_name, "любой") <= 2):
        country_name = random.choices(list(countries_potw["all"] - countries_history), k=1)[0] # выбираем любую страну ("all" — без привязки к части света)
        flag_path = data[country_name]["flag"]
        map_path = data[country_name]["map"]
        description = data[country_name]["description"]["Общее описание"]
    else:
        dist_best = 3
        country_name_closest = ""
        for country in countries_potw["all"]: # идём по всем странам
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


def leaderboard(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    
    leaderboard = db.sort_values(by='score_best', ascending=False)
    leaderboard.index = pd.RangeIndex(start=1, stop=len(leaderboard)+1, step=1)
    leaderboard_user = leaderboard.loc[leaderboard["chat_id"] == chat_id]
    leaderboard = leaderboard.head(LEADERBOARD_SIZE)
    
    leaderboard = leaderboard[["user_name", "score_best"]]
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    string = ""
    for i in leaderboard.index:
        string += f"{medals[i] if i in medals.keys() else i}: {leaderboard['user_name'][i]}, набравший(ая) {leaderboard['score_best'][i]} баллов!\n"
    string += f"\nВаше текущее место - {leaderboard_user.index[0]}, с суммой баллов {leaderboard_user['score_best'].iloc[0]}!{'🎉' if leaderboard_user.index[0] <=LEADERBOARD_SIZE else ''}"
    update.message.reply_text(string, reply_markup=kb_basic)
    
    
# def error(update: Update, context: CallbackContext) -> None:
#     logger.warning(f'Update {update} caused error {context.error}')


def main():
    updater = Updater(TOKEN, request_kwargs={'read_timeout': 30, 'connect_timeout': 30}) # API для взаимодействия с ботом

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
    dispatcher.add_handler(MessageHandler(Filters.regex(r"[В|в]ыведи таблицу лидеров"), leaderboard))
    dispatcher.add_handler(MessageHandler(Filters.regex(r"[В|в]ыбрать часть света"), choose_potw))
    dispatcher.add_handler(CallbackQueryHandler(choose_potw_))
    dispatcher.add_handler(MessageHandler(Filters.text, answer_flag)) 
    
    # dispatcher.add_error_handler(error)

    updater.start_polling() # Запуск бота

    # Ожидание завершения работы
    updater.idle()

if __name__ == '__main__':
    main()