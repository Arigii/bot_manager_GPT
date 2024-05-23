import threading
import time
from task_actions import *
from gpt import ask_gpt  # модуль для работы с GPT


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
    add_task(message)


@bot.message_handler(commands=['edit'])
def select_edit_task(message):
    list_tasks(message)
    edit_task(message)


@bot.message_handler(commands=['list'])
def list_tasks(message):
    chat_id = message.chat.id
    db.add_user(chat_id)
    db.update_list(chat_id)
    lists_task = print_list(chat_id)
    bot.send_message(chat_id, lists_task, reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(commands=['delete'])
def delete_task(message):
    list_tasks(message)
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
        analys = print_list(chat_id)
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
