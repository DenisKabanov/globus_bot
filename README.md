# Проект "Глобус".
Проект "Глобус" образовательно-развлекательного направления в сфере географии и этнографии.

**Используемые языки:**
* Python


## Project structure:
    .
    ├── data                        # общая папка под данные о странах
    │   ├── <country_name>          # папка с данными под конкретную страну "country_name"
    │   │   ├── description.txt     # файл с подсказками и общим описанием страны
    │   │   ├── flag.png            # файл с флагом страны
    │   │   └── map.png             # файл с географическим положением страны
    │   └── ...
    ├── db                          # папка под базу данных
    │   └── users.json              # файл базы данных с историей взаимодействия пользователей с приложением
    ├── extra                       # папка под дополнительные файлы
    │   ├── win_potw.gif            # гиф-анимация для пользователей, что прошли все страны в одной части света
    │   ├── win.gif                 # гиф-анимация для пользователей, что прошли все страны
    │   └── zones.png               # изображение с частями света
    ├── src                         # папка под скрипты
    │   └── bot.py                  # файл для запуска бота
    ├── README.md                   # файл, содержащий основную информацию о проекте
    ├── requirements.txt            # файл со списком необходимых библиотек для работы проекта
    ├── .env                        # файл, содержащий особые переменные окружения (токен для бота)
    └── .gitignore                  # файл, описывающий что git должен игнорировать в репозитории


## Requirements:
Файл `requirements.txt` содержит необходимые библиотеки Python для запуска вложенных файлов.

Они могут быть установлены следующей командой:
```
pip install --user -r requirements.txt
```


## Setup:
Настройки для приложения описаны в файле `.env`.

Файл `./src/bot.py` необходим для запуска приложения, в нём же описана основная его логика:
```
python ./src/bot.py
```


## Bot usage:
Ссылка на приложение: 
* https://t.me/Globus_project_bot

Для взаимодействия с приложением нужно использовать следующие команды:
* '<b>загадай</b>' — для загадывания страны;
* <b><название_cтраны></b> — для отгадывания страны;
* '<b>подскажи *</b>', где * это слово из (природу, достопримечательности, культуру, язык, исторический факт, города, часть названия, буквы) — для получения соответствующей подсказки;
* '<b>сдаюсь</b>' — чтобы признать поражение и узнать, какой стране принадлежит флаг;
* '<b>расскажи о стране *</b>', где * это название страны — чтобы бот мог поведать информацию о ней, без загадывания (для произвольной страны вместо * нужно написать 'любой');
* '<b>выведи таблицу лидеров</b>' — чтобы посмотреть рейтинг лучших игроков, а также узнать свою позицию в этом списке;
* '<b>выбрать часть света</b>' — для загадывания стран только из определённой части света, если ничего не выбрано, то загадываются все страны;
* '<b>очистить историю</b>' — для сброса истории взаимодействия с приложением и начала новой игры.