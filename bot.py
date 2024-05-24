import threading
import time
from gpt import ask_gpt  # модуль для работы с GPT
from validators import *
import logging
import telebot
from telebot import types
from database import Database

# подтягиваем функции из database файла
from creds import get_bot_token  # модуль для получения bot_token
from config import LOGS

# настраиваем запись логов в файл
logging.basicConfig(filename=LOGS, level=logging.INFO,
                    format="%(asctime)s FILE: %(filename)s IN: %(funcName)s MESSAGE: %(message)s", filemode="w")

bot = telebot.TeleBot(get_bot_token())  # создаём объект бота
db = Database()


# обрабатываем команду /debug - отправляем файл с логами
@bot.message_handler(commands=['debug'])
def debug(message):
    with open(LOGS, "rb") as f:
        bot.send_document(message.chat.id, f)


# функция для создания клавиатуры
def create_keyboard(buttons_list):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(*buttons_list)
    return keyboard


@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    username = message.from_user.username
    db.add_user(chat_id)
    logging.info("Добавление пользователя в бд")
    bot.reply_to(message, f"Привет, {username}! Я бот-менеджер задач. Чтобы добавить задачу, используй команду /add.",
                 reply_markup=create_keyboard(["/help"]))


@bot.message_handler(commands=['help'])
def send_help(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, """
    Список доступных команд:
    /add - добавить задачу
    /list - показать список задач
    /delete - удалить задачу
    /edit - редактировать задачу
    /reminder - установить напоминание
    """, reply_markup=create_keyboard(["/add", "/list", "/delete", "/edit", "/reminder"]))


@bot.message_handler(commands=['add'])
def select_add_task(message):
    chat_id = message.chat.id
    db.add_user(chat_id)
    bot.send_message(chat_id, "Введите описание вашей задачи:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_category_step)


def process_category_step(message):
    db.add_task(message.chat.id, message.text)
    bot.reply_to(message, "Хотите добавить категорию к задаче? (Да/Нет)")
    bot.register_next_step_handler(message, select_category_step)


def select_category_step(message):
    chat_id = message.chat.id
    option = message.text.lower()
    if option == "да":
        response = category_list(db) + "\nВыберите номер категории из списка: "
        bot.reply_to(message, response)
        bot.register_next_step_handler(message, process_category_accept)
    elif option == "нет":
        bot.send_message(chat_id, "Задача добавлена без категории. Хотите добавить дату и время к задаче? (Да/Нет)")
        bot.register_next_step_handler(message, select_datetime_step)
    else:
        bot.send_message(chat_id, "Пожалуйста, введите 'Да' или 'Нет'.")
        bot.register_next_step_handler(message, select_category_step)


def process_category_accept(message):
    chat_id = message.chat.id
    category_id = int(message.text)
    try:
        if 1 <= category_id <= 4:
            # Получаем последнюю добавленную задачу пользователя
            task_id = db.get_last_task(chat_id)[0]
            if task_id:
                db.add_category(task_id, category_id)
                bot.reply_to(message, "Успешно присвоена категория. Хотите добавить дату и время к задаче? (Да/Нет)")
                bot.register_next_step_handler(message, select_datetime_step)
            else:
                bot.reply_to(message, "Не удалось найти последнюю задачу. Попробуйте еще раз.")
        else:
            bot.reply_to(message, "Неверный номер категории. Пожалуйста, выберите номер от 1 до 4.")
            bot.register_next_step_handler(message, process_category_accept)
    except ValueError:
        bot.reply_to(message, "Пожалуйста, введите корректный номер категории.")
        bot.register_next_step_handler(message, process_category_accept)


def select_datetime_step(message):
    chat_id = message.chat.id
    option = message.text.lower()
    if option == "да":
        bot.reply_to(message, "Выберите дату в формате ГГГГ-ММ-ДД")
        bot.register_next_step_handler(message, select_date_validator)
    elif option == "нет":
        bot.send_message(chat_id, "Задача добавлена без даты и времени.")
    else:
        bot.send_message(chat_id, "Пожалуйста, введите 'Да' или 'Нет'.")
        bot.register_next_step_handler(message, select_datetime_step)


def select_date_validator(message):
    chat_id = message.chat.id
    date = message.text
    lock_start_time = True
    if not validate_date(date):
        bot.reply_to(message, "Введена дата неправильного формата. Пожалуйста, введите в формате ГГГГ-ММ-ДД.")
        bot.register_next_step_handler(message, select_date_validator)
        return
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    if date < current_date:
        bot.send_message(chat_id, "Ошибка: Дата задачи должна быть позже текущего времени.")
        bot.register_next_step_handler(message, select_date_validator)
        return
    if date > current_date:
        lock_start_time = False
    task = db.get_tasks(chat_id)[-1]
    task_id = task[0]
    db.add_date(task_id, date, chat_id)
    bot.reply_to(message, "Дата успешно выбрана. Выбрать время (Да/Нет)?")
    bot.register_next_step_handler(message, select_time, lock_start_time)


def select_time(message, lock_start_time):
    chat_id = message.chat.id
    option = message.text.lower()
    if option == "да":
        bot.reply_to(message, "Введите время начала задачи в формате ЧЧ:ММ")
        bot.register_next_step_handler(message, process_time_validator, lock_start_time)
    elif option == "нет":
        bot.send_message(chat_id, "Дата добавлена успешно без времени!")
    else:
        bot.send_message(chat_id, "Пожалуйста, введите 'Да' или 'Нет'.")
        bot.register_next_step_handler(message, select_time, lock_start_time)


def process_time_validator(message, lock_start_time):
    chat_id = message.chat.id
    start_time = message.text
    if not validate_time(start_time):
        bot.send_message(chat_id, "Некорректное время начала задачи. Пожалуйста, введите в формате ЧЧ:ММ.")
        bot.register_next_step_handler(message, process_time_validator, lock_start_time)
        return
    current_time = datetime.datetime.now().strftime("%H:%M")
    if start_time <= current_time and lock_start_time:
        bot.send_message(chat_id, "Ошибка: Время начала задачи должно быть позже текущего времени.")
        bot.register_next_step_handler(message, process_time_validator, lock_start_time)
        return
    bot.reply_to(message, "Введите время окончания задачи в формате ЧЧ:ММ")
    bot.register_next_step_handler(message, process_end_time_validator, start_time, lock_start_time)


def process_end_time_validator(message, start_time, lock_start_time):
    chat_id = message.chat.id
    end_time = message.text
    if not validate_time(end_time):
        bot.send_message(chat_id, "Некорректное время окончания задачи. Пожалуйста, введите в формате ЧЧ:ММ.")
        bot.register_next_step_handler(message, process_end_time_validator, start_time, lock_start_time)
        return
    if end_time <= start_time:
        bot.send_message(chat_id, "Ошибка: Время окончания задачи должно быть позже времени начала.")
        bot.register_next_step_handler(message, process_end_time_validator, start_time, lock_start_time)
        return
    task = db.get_tasks(chat_id)[-1]
    task_id = task[0]
    db.add_time(task_id, start_time, end_time, chat_id)
    bot.send_message(chat_id, "Время к задаче добавлено успешно!")


@bot.message_handler(commands=['edit'])
def select_edit_task(message):
    chat_id = message.chat.id
    list_tasks(message)
    if not db.get_tasks(chat_id):
        return
    msg = bot.reply_to(message, "Введите номер задачи, которую хотите отредактировать:")
    bot.register_next_step_handler(msg, process_edit_step)


def process_edit_step(message):
    try:
        chat_id = message.chat.id
        task_id = int(message.text)
        task = db.get_task_by_id(task_id, chat_id)
        if task:
            bot.send_message(chat_id, "Что вы хотите изменить?\n1. Описание\n2. Дату"
                                      "\n3. Время начала и время окончания\n4. Категория"
                                      "\n Напоминание редактрируется отдельной командой /reminder.",
                             reply_markup=types.ReplyKeyboardRemove())
            bot.register_next_step_handler(message, lambda msg: process_edit_choice(msg, task_id))
        else:
            bot.reply_to(message, "Задача с указанным номером не найдена.")
            bot.register_next_step_handler(message, process_edit_step)
    except ValueError:
        bot.reply_to(message, "Неверный формат номера задачи. Пожалуйста, введите числовое значение.")
        bot.register_next_step_handler(message, process_edit_step)


def process_edit_choice(message, task_id):
    choice = message.text.strip()
    if choice == '1':
        msg = bot.reply_to(message, "Введите новое описание задачи:")
        bot.register_next_step_handler(msg, lambda msg: process_edit_description_step(msg, task_id))
    elif choice == '2':
        msg = bot.reply_to(message, "Введите новую дату задачи в формате ГГГГ-ММ-ДД:")
        bot.register_next_step_handler(msg, lambda msg: process_edit_date_step(msg, task_id))
    elif choice == '3':
        msg = bot.reply_to(message, "Введите новое время начала задачи в формате ЧЧ:ММ:")
        bot.register_next_step_handler(msg, lambda msg: process_edit_start_time_step(msg, task_id))
    elif choice == '4':
        response = category_list(db) + "\nВведите номер категории:"
        msg = bot.reply_to(message, response)
        bot.register_next_step_handler(msg, lambda msg: process_edit_category(msg, task_id))
    else:
        bot.reply_to(message, "Пожалуйста, выберите один из пунктов: 1, 2, 3 или 4.")
        bot.register_next_step_handler(message, lambda msg: process_edit_choice(msg, task_id))


def process_edit_description_step(message, task_id):
    new_description = message.text
    chat_id = message.chat.id
    db.update_task(task_id, new_description, chat_id)
    bot.send_message(message.chat.id, "Описание задачи успешно обновлено.")


def process_edit_date_step(message, task_id):
    chat_id = message.chat.id
    new_date = message.text
    if not validate_date(new_date):
        bot.reply_to(message, "Некорректный формат даты. Пожалуйста, введите в формате ГГГГ-ММ-ДД.")
        bot.register_next_step_handler(message, lambda msg: process_edit_date_step(msg, task_id))
        return
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d")
    if new_date < current_datetime:
        bot.reply_to(message, "Дата задачи должна быть позже текущего времени.")
        bot.register_next_step_handler(message, lambda msg: process_edit_date_step(msg, task_id))
        return
    db.update_date(task_id, new_date, chat_id)
    bot.send_message(chat_id, "Дата задачи успешно обновлена.")


def process_edit_start_time_step(message, task_id):
    chat_id = message.chat.id
    new_start_time = message.text
    if not validate_time(new_start_time):
        bot.reply_to(message, "Некорректный формат времени. Пожалуйста, введите в формате ЧЧ:ММ.")
        bot.register_next_step_handler(message, lambda msg: process_edit_start_time_step(msg, task_id))
        return
    current_time = datetime.datetime.now().strftime("%H:%M")
    if new_start_time <= current_time:
        bot.send_message(chat_id, "Ошибка: Время начала задачи должно быть позже текущего времени.")
        bot.register_next_step_handler(message, process_time_validator)
        return
    db.update_task_start_time(task_id, new_start_time, chat_id)
    bot.send_message(chat_id, "Время начала задачи успешно обновлено. Выберите в том же формате время окончания")
    bot.register_next_step_handler(message, process_edit_end_time_step, task_id, new_start_time)


def process_edit_end_time_step(message, task_id, new_start_time):
    chat_id = message.chat.id
    new_end_time = message.text
    if not validate_time(new_end_time):
        bot.reply_to(message, "Некорректный формат времени. Пожалуйста, введите в формате ЧЧ:ММ.")
        bot.register_next_step_handler(message, lambda msg: process_edit_end_time_step(msg, task_id, new_start_time))
        return
    if new_end_time <= new_start_time:
        bot.send_message(chat_id, "Ошибка: Время окончания задачи должно быть позже времени начала.")
        bot.register_next_step_handler(message, lambda msg: process_edit_end_time_step(msg, task_id, new_start_time))
        return
    db.update_task_end_time(task_id, new_end_time, chat_id)
    bot.send_message(chat_id, "Время окончания задачи успешно обновлено.")


def process_edit_category(message, task_id):
    try:
        new_category = int(message.text)
        if new_category not in [1, 2, 3, 4]:
            raise ValueError("Неверный номер категории")
    except ValueError:
        bot.reply_to(message, "Пожалуйста, введите корректный номер категории (1, 2, 3 или 4).")
        bot.register_next_step_handler(message, lambda msg: process_edit_category(msg, task_id))
        return

    chat_id = message.chat.id
    db.update_category(task_id, new_category, chat_id)
    bot.send_message(chat_id, "Категория задачи успешно обновлена.")


@bot.message_handler(commands=['list'])
def list_tasks(message):
    chat_id = message.chat.id
    db.add_user(chat_id)
    db.update_list(chat_id)
    lists_task = print_list(chat_id, db)
    bot.send_message(chat_id, lists_task, reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(commands=['delete'])
def delete_task(message):
    chat_id = message.chat.id
    list_tasks(message)
    if not db.get_tasks(chat_id):
        return
    msg = bot.reply_to(message, "Введите номер задачи, которую хотите удалить:")
    bot.register_next_step_handler(msg, process_delete_step)


def process_delete_step(message):
    chat_id = message.chat.id
    db.delete_task(int(message.text), chat_id)
    bot.send_message(chat_id, "Задача удалена успешно!", reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(commands=['reminder'])
def set_reminder(message):
    list_tasks(message)
    msg = bot.reply_to(message, "Введите номер задачи, для которой хотите установить напоминание:")
    bot.register_next_step_handler(msg, process_reminder_step)


def process_reminder_step(message):
    msg = bot.reply_to(message, "Введите дату и время напоминания (в формате ГГГГ-ММ-ДД ЧЧ:ММ):",
                       reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda msg: process_reminder_date_step(msg, message.text))


def process_reminder_date_step(message, task_id):
    chat_id = message.chat.id
    reminder = message.text
    try:
        reminder_datetime = datetime.datetime.strptime(reminder, "%Y-%m-%d %H:%M")
    except ValueError:
        bot.send_message(chat_id, "Некорректный формат даты и времени. Пожалуйста, введите в формате ГГГГ-ММ-ДД ЧЧ:ММ.")
        bot.register_next_step_handler(message, lambda msg: process_reminder_date_step(msg, task_id))
        return

    current_datetime = datetime.datetime.now()
    if reminder_datetime <= current_datetime:
        bot.send_message(chat_id, "Ошибка: Время напоминания должно быть позже текущего времени.")
        bot.register_next_step_handler(message, lambda msg: process_reminder_date_step(msg, task_id))
        return

    task = db.get_task_by_id(task_id, chat_id)
    if not task:
        bot.send_message(chat_id, "Ошибка: Задача с указанным номером не найдена.")
        return

    # Проверяем наличие даты и времени окончания задачи
    task_date = task[4]
    task_end_time = task[6]

    if task_date and task_end_time:
        task_end_datetime_str = f"{task_date} {task_end_time}"
        try:
            task_end_datetime = datetime.datetime.strptime(task_end_datetime_str, "%Y-%m-%d %H:%M")
        except ValueError:
            bot.send_message(chat_id, "Ошибка в формате даты или времени окончания задачи.")
            return

        if reminder_datetime >= task_end_datetime:
            bot.send_message(chat_id, "Ошибка: Время напоминания должно быть раньше времени окончания задачи.")
            bot.register_next_step_handler(message, lambda msg: process_reminder_date_step(msg, task_id))
            return

    db.set_reminder(task_id, reminder, chat_id)
    bot.send_message(chat_id, "Напоминание установлено успешно!")


def check_reminders():
    while True:
        tasks = db.get_all_tasks_with_reminders()
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # Пользовательские напоминания
        for task in tasks:
            (task_id, user_id, sequence_number, task_description, task_date, start_time, end_time, reminder_time,
             category_id) = task
            if current_time == reminder_time:
                bot.send_message(user_id, f"Тук-тук, вы просили меня напомнить: {task_description}")
                db.delete_remind(None, user_id)

        # Автоматические напоминания
        tasks_auto = db.get_all_datatime()
        for task in tasks_auto:
            user_id, task_description, task_date, start_time, end_time, reminder_time = task

            # Напоминание за 10 минут до начала задачи
            if task_date and start_time:
                start_datetime_str = f"{task_date} {start_time}"
                try:
                    start_datetime = datetime.datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M")
                    if ((start_datetime - datetime.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M") == current_time
                            and (start_datetime - datetime.timedelta(minutes=10)).strftime(
                                "%Y-%m-%d %H:%M") != reminder_time):
                        bot.send_message(user_id,
                                         f"Напоминание: Задача '{task_description}' начинается через 10 минут.")
                except ValueError as e:
                    print(e)

            # Напоминание за 10 минут до окончания задачи
            if task_date and end_time:
                end_datetime_str = f"{task_date} {end_time}"
                try:
                    end_datetime = datetime.datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M")
                    if ((end_datetime - datetime.timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M") == current_time and
                            (end_datetime - datetime.timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M") != reminder_time):
                        bot.send_message(user_id,
                                         f"Напоминание: Задача '{task_description}' заканчивается через 5 минут.")
                except ValueError as e:
                    print(e)

        time.sleep(60)  # Проверяем каждую минуту


@bot.message_handler(commands=['analysis'])
def analysis_gpt_answer(message):
    chat_id = message.chat.id
    try:
        bot.send_message(chat_id, "Генерирую ответ, подождите  ✍(◔◡◔)",
                         reply_markup=types.ReplyKeyboardRemove())

        # отправляем запрос к GPT
        analys = print_list(chat_id, db)
        status_gpt, answer_gpt = ask_gpt(analys)  # передаем сообщение

        # обрабатываем ответ от GPT
        if not status_gpt:
            # если что-то пошло не так — уведомляем пользователя и прекращаем выполнение функции
            bot.send_message(chat_id, answer_gpt)
            return
        bot.reply_to(message, answer_gpt)  # отвечаем пользователю текстом
        logging.info(f"Успешная отправка ответа gpt пользователю {chat_id}")
    except Exception as e:
        logging.error(e)  # если ошибка — записываем её в логи
        bot.send_message(message.from_user.id, "Не получилось ответить. Попробуй написать другое сообщение")


reminder_thread = threading.Thread(target=check_reminders)
reminder_thread.start()

if __name__ == "__main__":
    bot.polling()
