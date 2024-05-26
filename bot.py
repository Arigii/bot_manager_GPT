import logging
import threading
import time
import datetime

import telebot
from telebot import types
from creds import get_bot_token  # модуль для получения bot_token
from config import LOGS  # путь до лог файла

from gpt import ask_gpt  # модуль для работы с GPT

# подтягиваем функции из database файла
from database import (add_user, add_task, get_last_task, add_category, add_date, add_time, get_task_by_id,
                      update_task, update_date, update_task_start_time, update_category, update_task_end_time,
                      update_list, delete_task, delete_remind, get_all_datatime, get_all_tasks_with_reminders,
                      create_tables, get_tasks)

# модуль для валидирования
from validators import category_list, validate_date, validate_time, print_list

# настраиваем запись логов в файл
logging.basicConfig(filename=LOGS, level=logging.INFO,
                    format="%(asctime)s FILE: %(filename)s IN: %(funcName)s MESSAGE: %(message)s", filemode="w")

bot = telebot.TeleBot(get_bot_token())  # создаём объект бота


# обрабатываем команду /debug - отправляем файл с логами
@bot.message_handler(commands=['debug'])
def debug(message):
    try:
        with open(LOGS, "rb") as f:
            bot.send_document(message.chat.id, f)
    except ValueError as e:
        bot.reply_to(message, "Ошибка выгрузки логов. Файл поврежден или пуст.")
        logging.error(f"Ошибка выгрузки лог файлов: {e}")


# функция для создания клавиатуры
def create_keyboard(buttons_list):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(*buttons_list)
    return keyboard


# приветственное сообщение, добавление пользователя в бд
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        chat_id = message.chat.id
        username = message.from_user.username
        add_user(chat_id)
        logging.info(f"Добавление {username} в базу данных под {chat_id}")
        bot.reply_to(message,
                     f"Привет, {username}! Я бот-менеджер задач. Чтобы добавить задачу, используй команду /add. "
                     f"Для подробной информации используй команду /help.",
                     reply_markup=create_keyboard(["/help", "/add"]))
    except ValueError as e:
        bot.reply_to(message, "Ошибка добавления в базу данных! Свяжусь с создателем.")
        logging.error(f"Ошибка добавления пользователя {message.chat.id} к бд: {e}")


# сообщение с командами и подробным описанием бота
@bot.message_handler(commands=['help'])
def send_help(message):
    chat_id = message.chat.id
    message_info = """\n
    Список доступных команд:
    /add - добавить задачу
    /list - показать список задач
    /delete - удалить задачу
    /edit - редактировать задачу
    /reminder - установить напоминание
    /analysis - сделать анализ списка
    """
    bot.send_message(chat_id, "Привет, я бот-менеджер, который помогает распределять задачи по матрицей Эйзенхауэра и "
                              "расставлять напоминания. Как и любой менеджер-помощник, я буду использовать список "
                              "заметок, но это пока в разработке. Я могу уже на данном этапе анализировать весь твой "
                              "список и отправлять тебе рекомендации и предложения. Я использую автоматические "
                              "напоминания (при заданной дате, времени начала и конца задачи), которые пока что нельзя "
                              "выключить. В раработке система аутентификации, поддержка сторонних сервисов, поддержка "
                              "отчетов, смс уведомления, автоматическое разбиение на категории, расшифровывание задач "
                              "по голосу. Проектируется улучшенный интерфейс!!!\nВот моя ссылка в телеграм для "
                              "сообщения ошибок - https://t.me/Remminders"
                              "\n Вот репозиторий этого бота https://github.com/Arigii/bot_manager_GPT \nСоздан с "
                              "помощью инструментария GPTYandex." + message_info,
                     reply_markup=create_keyboard(["/add", "/list", "/delete", "/edit", "/reminder"]))


@bot.message_handler(commands=['add'])
def select_add_task(message):
    try:
        chat_id = message.chat.id
        add_user(chat_id)
        logging.info(f"Добавление в базу данных в пользователя под {chat_id}")
        bot.send_message(chat_id, "Введите описание вашей задачи. Чем грамотнее и чем подробнее она описана - тем "
                                  "лучше будет работать анализ от нейросети. Помните об этом!"
                                  " Для отмены напишите 'отмена'.",
                         reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, process_category_step)
    except ValueError as e:
        bot.reply_to(message, "Ошибка добавления пользователя. Свяжусь с разработчиком, извините за неудобства")
        logging.error(f"Ошибка добавления пользователя {message.chat.it} в базу данных: {e}")


def process_category_step(message):
    try:
        if message.text.lower() == 'отмена':
            bot.reply_to(message, "Добавление задачи отменено")
            return
        chat_id = message.chat.id
        add_task(message.chat.id, message.text)
        logging.info(f"Добавление описания задачи у пользователя {chat_id}")
        bot.send_message(chat_id, "Категории Эйзенхауэра - категории, которые разграничивают ваши дела по пунктам."
                                  " Хотите добавить категорию к задаче? (Да/Нет)",
                         reply_markup=create_keyboard(["Да", "Нет"]))
        bot.register_next_step_handler(message, select_category_step)
    except ValueError as e:
        bot.reply_to(message, "Ой! Не получилось добавить описание задачи. Пойду связываться с разработчиком")
        logging.error(f"Ошибка добавления у пользователя {message.chati.it} задачи: {e}")


def select_category_step(message):
    try:
        chat_id = message.chat.id
        option = message.text.lower()
        if option == "да":
            response = category_list() + "5. Выход без использования категории.\nВыберите номер категории из списка: "
            bot.send_message(chat_id, response, reply_markup=create_keyboard(['1', '2', '3', '4', '5']))
            bot.register_next_step_handler(message, process_category_accept)
        elif option == "нет":
            bot.send_message(chat_id, "Задача добавлена без категории. Хотите добавить дату и время к задаче? (Да/Нет)",
                             reply_markup=create_keyboard(['Да', 'Нет']))
            bot.register_next_step_handler(message, select_datetime_step)
        else:
            bot.send_message(chat_id, "Пожалуйста, введите 'Да' или 'Нет'.")
            bot.register_next_step_handler(message, select_category_step)
    except ValueError as e:
        bot.reply_to(message, "Произошла ошибка вывода списка. Попробуйте позже")
        logging.error(f"Ошибка вывода списка {e}")


def process_category_accept(message):
    chat_id = message.chat.id
    category_id = int(message.text)
    try:
        if 1 <= category_id <= 4:
            # Получаем последнюю добавленную задачу пользователя
            task_id = get_last_task(chat_id)[0]
            if task_id:
                add_category(task_id, category_id)
                logging.info(f"Добавление категории задачи у пользователя {chat_id}")
                bot.send_message(message,
                                 "Успешно присвоена категория. Хотите добавить дату и время к задаче? (Да/Нет)")
                bot.register_next_step_handler(message, select_datetime_step)
            else:
                bot.reply_to(message, "Не удалось найти последнюю задачу. Попробуйте еще раз.",
                             reply_parameters=types.ReplyKeyboardRemove())
        elif category_id == 5:
            bot.send_message(chat_id, "Хорошо, я оставлю только описание задачи. Вы всегда можете изменить задачу",
                             reply_markup=types.ReplyKeyboardRemove())
        else:
            bot.reply_to(message, "Неверный номер категории. Пожалуйста, выберите номер от 1 до 4.")
            bot.register_next_step_handler(message, process_category_accept)
    except ValueError as e:
        bot.reply_to(message, "Ошибка выбора категории")
        logging.error(f"Ошибка выбора категории: {e}")
        bot.register_next_step_handler(message, process_category_accept)


def select_datetime_step(message):
    chat_id = message.chat.id
    option = message.text.lower()
    if option == "да":
        bot.reply_to(message, "Введите дату в формате ГГГГ-ММ-ДД", reply_parameters=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, select_date_validator)
    elif option == "нет":
        bot.send_message(chat_id, "Задача добавлена без даты и времени.", reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(chat_id, "Пожалуйста, введите 'Да' или 'Нет'.")
        bot.register_next_step_handler(message, select_datetime_step)


def select_date_validator(message):
    try:
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
        task = get_tasks(chat_id)[-1]
        task_id = task[0]
        add_date(task_id, date, chat_id)
        logging.info(f"Добавление даты для задачи пользователя: {chat_id}")
        bot.reply_to(message, "Дата успешно выбрана. Выбрать время (Да/Нет)?",
                     reply_parameters=create_keyboard(['Да', 'Нет']))
        bot.register_next_step_handler(message, select_time, lock_start_time)
    except ValueError as e:
        bot.reply_to(message, "Произошла ошибка обработки даты. Попробуйте позже",
                     reply_parameters=types.ReplyKeyboardRemove())
        logging.error(f"Ошибка при обработке даты: {e}")


def select_time(message, lock_start_time):
    chat_id = message.chat.id
    option = message.text.lower()
    if option == "да":
        bot.reply_to(message, "Введите время начала задачи в формате ЧЧ:ММ",
                     reply_parameters=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, process_time_validator, lock_start_time)
    elif option == "нет":
        bot.send_message(chat_id, "Дата добавлена успешно без времени!", reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(chat_id, "Пожалуйста, введите 'Да' или 'Нет'.")
        bot.register_next_step_handler(message, select_time, lock_start_time)


def process_time_validator(message, lock_start_time):
    try:
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
    except ValueError as e:
        bot.reply_to(message, f"Ошибка обработки времени. Попробуйте в следуюищй раз.")
        logging.error(f"Ошибка обработки времени: {e}")


def process_end_time_validator(message, start_time, lock_start_time):
    try:
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
        task = get_tasks(chat_id)[-1]
        task_id = task[0]
        add_time(task_id, start_time, end_time, chat_id)
        logging.info(f"Сохранение даты начала и дата окончания у задачи {task_id} пользователя {chat_id}")
        bot.send_message(chat_id, "Время к задаче добавлено успешно!")
    except ValueError as e:
        bot.reply_to(message, "Ошибка при обработке времени окончания. Попробуйте в следующий раз")
        logging.error(f"Ошибка обработки окончания времени: {e}")


@bot.message_handler(commands=['edit'])
def select_edit_task(message):
    try:
        chat_id = message.chat.id
        list_tasks(message)
        if not get_tasks(chat_id):
            return
        bot.reply_to(message, "Введите номер задачи, которую хотите отредактировать:",
                     reply_parameters=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, process_edit_step)
    except ValueError as e:
        bot.reply_to(message, "Ошибка вывода списка задач, поробуйте в следующий раз")
        logging.error(f"Ошибка вывода списка задач в select_edit_task: {e}")


def process_edit_step(message):
    try:
        chat_id = message.chat.id
        task_id = int(message.text)
        task = get_task_by_id(task_id, chat_id)
        if task:
            bot.send_message(chat_id, "Что вы хотите изменить?\n1. Описание\n2. Дату"
                                      "\n3. Время начала и время окончания\n4. Категория"
                                      "\n5 Выход.\n Напоминание редактрируется отдельной командой /reminder.",
                             reply_markup=types.ReplyKeyboardRemove())
            bot.register_next_step_handler(message, lambda msg: process_edit_choice(msg, task_id))
        else:
            bot.reply_to(message, "Задача с указанным номером не найдена.")
            bot.register_next_step_handler(message, process_edit_step)
    except ValueError as e:
        bot.reply_to(message, "Ошибка. Пожалуйста, попробуйте позже.")
        logging.error(f"Ошибка вывода списка в process_edit_step: {e}")
        bot.register_next_step_handler(message, process_edit_step)


def process_edit_choice(message, task_id):
    try:
        choice = message.text.strip()
        if choice == '1':
            msg = bot.reply_to(message, "Введите новое описание задачи:")
            bot.register_next_step_handler(msg, process_edit_description_step, task_id)
        elif choice == '2':
            msg = bot.reply_to(message, "Введите новую дату задачи в формате ГГГГ-ММ-ДД:")
            bot.register_next_step_handler(msg, process_edit_date_step, task_id)
        elif choice == '3':
            msg = bot.reply_to(message, "Введите новое время начала задачи в формате ЧЧ:ММ:")
            bot.register_next_step_handler(msg, process_edit_start_time_step, task_id)
        elif choice == '4':
            response = category_list() + "\nВведите номер категории:"
            msg = bot.reply_to(message, response)
            bot.register_next_step_handler(msg, process_edit_category, task_id)
        elif choice == '5':
            bot.reply_to(message, "Хорошо, забудем про редактирование.")
            return
        else:
            bot.reply_to(message, "Пожалуйста, выберите один из пунктов: 1, 2, 3 или 4.")
            bot.register_next_step_handler(message, process_edit_choice, task_id)
    except ValueError as e:
        logging.error(f"Ошибка в process_edit_choice: {e} ")


def process_edit_description_step(message, task_id):
    try:
        new_description = message.text
        chat_id = message.chat.id
        update_task(task_id, new_description, chat_id)
        bot.send_message(message.chat.id, "Описание задачи успешно обновлено.")
    except ValueError as e:
        bot.reply_to(message, "Произошла ошибка, попробуйте в следующий раз")
        logging.error(f"Ошибка обновления описания задачи: {e}")


def process_edit_date_step(message, task_id):
    try:
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
        update_date(task_id, new_date, chat_id)
        bot.send_message(chat_id, "Дата задачи успешно обновлена.")
    except ValueError as e:
        bot.reply_to(message, "Произошла ошибка, попробуйте в следующий раз")
        logging.error(f"Произошла ошибка изменения даты: {e}")


def process_edit_start_time_step(message, task_id):
    try:
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
        update_task_start_time(task_id, new_start_time, chat_id)
        bot.send_message(chat_id, "Время начала задачи успешно обновлено. Выберите в том же формате время окончания")
        bot.register_next_step_handler(message, process_edit_end_time_step, task_id, new_start_time)
    except ValueError as e:
        bot.reply_to(message, "Произошла ошибка, попробуйте в следующий раз")
        logging.error(f"Произошла ошибка изменения даты: {e}")


def process_edit_end_time_step(message, task_id, new_start_time):
    try:
        chat_id = message.chat.id
        new_end_time = message.text
        if not validate_time(new_end_time):
            bot.reply_to(message, "Некорректный формат времени. Пожалуйста, введите в формате ЧЧ:ММ.")
            bot.register_next_step_handler(message,
                                           lambda msg: process_edit_end_time_step(msg, task_id, new_start_time))
            return
        if new_end_time <= new_start_time:
            bot.send_message(chat_id, "Ошибка: Время окончания задачи должно быть позже времени начала.")
            bot.register_next_step_handler(message,
                                           lambda msg: process_edit_end_time_step(msg, task_id, new_start_time))
            return
        update_task_end_time(task_id, new_end_time, chat_id)
        bot.send_message(chat_id, "Время окончания задачи успешно обновлено.")
    except ValueError as e:
        bot.reply_to(message, "Произошла ошибка, попробуйте в следующий раз")
        logging.error(f"Произошла ошибка изменения времени начала: {e}")


def process_edit_category(message, task_id):
    try:
        try:
            new_category = int(message.text)
            if new_category not in [1, 2, 3, 4]:
                raise ValueError("Неверный номер категории")
        except ValueError:
            bot.reply_to(message, "Пожалуйста, введите корректный номер категории (1, 2, 3 или 4).")
            bot.register_next_step_handler(message, process_edit_category, task_id)
            return
        chat_id = message.chat.id
        update_category(task_id, new_category, chat_id)
        bot.send_message(chat_id, "Категория задачи успешно обновлена.")
    except ValueError as e:
        bot.reply_to(message, "Произошла ошибка, попробуйте в следующий раз")
        logging.error(f"Произошла ошибка изменения даты окончания: {e}")


@bot.message_handler(commands=['list'])
def list_tasks(message):
    try:
        chat_id = message.chat.id
        add_user(chat_id)
        update_list(chat_id)
        lists_task = print_list(chat_id)
        bot.send_message(chat_id, lists_task, reply_markup=types.ReplyKeyboardRemove())
    except ValueError as e:
        bot.reply_to(message, "Ошибка вывода списка задач. Свяжусь с разработчиком")
        logging.error(f"Ошибка вывода списка задач: {e}")


@bot.message_handler(commands=['delete'])
def process_delete_task(message):
    try:
        chat_id = message.chat.id
        list_tasks(message)
        if not get_tasks(chat_id):
            return
        msg = bot.reply_to(message, "Введите номер задачи, которую хотите удалить:")
        bot.register_next_step_handler(msg, process_delete_step)
    except ValueError as e:
        logging.error(e)


def process_delete_step(message):
    try:
        chat_id = message.chat.id
        delete_task(int(message.text), chat_id)
        bot.send_message(chat_id, "Задача удалена успешно!", reply_markup=types.ReplyKeyboardRemove())
    except ValueError as e:
        logging.error(f"Ошибка удаления задачи: {e}")


@bot.message_handler(commands=['analysis'])
def analysis_gpt_answer(message):
    chat_id = message.chat.id
    try:
        bot.send_message(chat_id, "Генерирую ответ, подождите  ✍(◔◡◔)",
                         reply_markup=types.ReplyKeyboardRemove())

        # отправляем запрос к GPT
        analys = print_list(chat_id)
        if analys == "У вас нет задач.":
            bot.reply_to(message, "У вас нет задач.")
            return
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


@bot.message_handler(commands=['reminder'])
def set_reminder(message):
    list_tasks(message)
    bot.reply_to(message, "Введите номер задачи, для которой хотите установить напоминание:")
    bot.register_next_step_handler(message, process_reminder_step)


def process_reminder_step(message):
    try:
        task_id = message.text
        chat_id = message.chat.id
        task = get_task_by_id(task_id, chat_id)
        if not task:
            bot.send_message(chat_id, "Ошибка: Задача с указанным номером не найдена.")
            return
        bot.reply_to(message, "Введите дату и время напоминания (в формате ГГГГ-ММ-ДД ЧЧ:ММ):",
                     reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, process_reminder_date_step, task_id, task)
    except ValueError as e:
        bot.reply_to(message, "Ошибка вывода спика задач. Попробуйте в следующий раз")
        logging.error(f"Ошибка вывода списка задач в process_reminder_step: {e}")


def process_reminder_date_step(message, task_id, task):
    try:
        chat_id = message.chat.id
        reminder = message.text
        try:
            reminder_datetime = datetime.datetime.strptime(reminder, "%Y-%m-%d %H:%M")
        except ValueError:
            bot.send_message(chat_id,
                             "Некорректный формат даты и времени. Пожалуйста, введите в формате ГГГГ-ММ-ДД ЧЧ:ММ.")
            bot.register_next_step_handler(message, lambda msg: process_reminder_date_step(msg, task_id, task))
            return

        current_datetime = datetime.datetime.now()
        if reminder_datetime <= current_datetime:
            bot.send_message(chat_id, "Ошибка: Время напоминания должно быть позже текущего времени.")
            bot.register_next_step_handler(message, lambda msg: process_reminder_date_step(msg, task_id, task))
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
                bot.register_next_step_handler(message, lambda msg: process_reminder_date_step(msg, task_id, task))
                return

        set_reminder(task_id, reminder, chat_id)
        bot.send_message(chat_id, "Напоминание установлено успешно!")
    except ValueError as e:
        bot.reply_to(message, "Произошла ошибка обработки даты для напоминания. Попробуйте еще раз.")
        logging.error(f"Ошибка обработки даты для напоминания: {e}")


def check_reminders():
    while True:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            tasks = get_all_tasks_with_reminders()
            # Пользовательские напоминания
            for task in tasks:
                (task_id, user_id, sequence_number, task_description, task_date, start_time, end_time, reminder_time,
                 category_id) = task
                if current_time == reminder_time:
                    bot.send_message(user_id, f"Тук-тук, вы просили меня напомнить: {task_description}")
                    delete_remind(None, user_id)
        except ValueError as e:
            logging.error(f"Ошибка пользовательского напоминания: {e}")

        # Автоматические напоминания
        try:
            tasks_auto = get_all_datatime()
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
                        logging.error(f"Ошибка при напоминания начала задачи: {e}")

                # Напоминание за 10 минут до окончания задачи
                if task_date and end_time:
                    end_datetime_str = f"{task_date} {end_time}"
                    try:
                        end_datetime = datetime.datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M")
                        if ((end_datetime - datetime.timedelta(minutes=5)).strftime(
                                "%Y-%m-%d %H:%M") == current_time and
                                (end_datetime - datetime.timedelta(minutes=5)).strftime(
                                    "%Y-%m-%d %H:%M") != reminder_time):
                            bot.send_message(user_id,
                                             f"Напоминание: Задача '{task_description}' заканчивается через 5 минут.")
                    except ValueError as e:
                        logging.error(f"Ошибка при напоминания окончания задачи: {e}")
        except ValueError as e:
            logging.error(f"Ошибка автоматического напоминания: {e}")
        time.sleep(60)  # Проверяем каждую минуту


@bot.message_handler()
def hadnler_useless(message):
    bot.reply_to(message, "Воспользуйтесь командой /start или /help")


reminder_thread = threading.Thread(target=check_reminders)
reminder_thread.start()
logging.info("Старт асинхронного потока для напоминаний")

if __name__ == "__main__":
    bot.polling()
    create_tables()
    logging.info("Старт бота и создание бд")
