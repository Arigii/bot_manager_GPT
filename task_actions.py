from validators import *


@bot.message_handler(commands=['add'])
def add_task(message):
    chat_id = message.chat.id
    db.add_user(chat_id)
    bot.send_message(message, "Введите описание вашей задачи:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_category_step)


def process_category_step(message):
    db.add_task(message.chat.id, message.text)
    bot.reply_to(message, "Хотите добавить категорию к задаче? (Да/Нет)")
    bot.register_next_step_handler(message, select_category_step)


def select_category_step(message):
    chat_id = message.chat.id
    option = message.text.lower()
    if option == "да":
        response = category_list() + "\nВыберите номер категории из списка: "
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
    if not validate_date(date):
        bot.reply_to(message, "Введена дата неправильного формата. Пожалуйста, введите в формате ГГГГ-ММ-ДД.")
        bot.register_next_step_handler(message, select_date_validator)
        return
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    if date < current_date:
        bot.send_message(chat_id, "Ошибка: Дата задачи должна быть позже текущего времени.")
        bot.register_next_step_handler(message, select_date_validator)
        return
    task = db.get_tasks(chat_id)[-1]
    task_id = task[0]
    db.add_date(task_id, date, chat_id)
    bot.reply_to(message, "Дата успешно выбрана. Выбрать время (Да/Нет)?")
    bot.register_next_step_handler(message, select_time)


def select_time(message):
    chat_id = message.chat.id
    option = message.text.lower()
    if option == "да":
        bot.reply_to(message, "Введите время начала задачи в формате ЧЧ:ММ")
        bot.register_next_step_handler(message, process_time_validator)
    elif option == "нет":
        bot.send_message(chat_id, "Дата добавлена успешно без времени!")
    else:
        bot.send_message(chat_id, "Пожалуйста, введите 'Да' или 'Нет'.")
        bot.register_next_step_handler(message, select_time)


def process_time_validator(message):
    chat_id = message.chat.id
    start_time = message.text
    if not validate_time(start_time):
        bot.send_message(chat_id, "Некорректное время начала задачи. Пожалуйста, введите в формате ЧЧ:ММ.")
        bot.register_next_step_handler(message, process_time_validator)
        return
    current_time = datetime.datetime.now().strftime("%H:%M")
    if start_time <= current_time:
        bot.send_message(chat_id, "Ошибка: Время начала задачи должно быть позже текущего времени.")
        bot.register_next_step_handler(message, process_time_validator)
        return
    bot.reply_to(message, "Введите время окончания задачи в формате ЧЧ:ММ")
    bot.register_next_step_handler(message, process_end_time_validator, start_time)


def process_end_time_validator(message, start_time):
    chat_id = message.chat.id
    end_time = message.text
    if not validate_time(end_time):
        bot.send_message(chat_id, "Некорректное время окончания задачи. Пожалуйста, введите в формате ЧЧ:ММ.")
        bot.register_next_step_handler(message, process_end_time_validator, start_time)
        return
    if end_time <= start_time:
        bot.send_message(chat_id, "Ошибка: Время окончания задачи должно быть позже времени начала.")
        bot.register_next_step_handler(message, process_end_time_validator, start_time)
        return
    task = db.get_tasks(chat_id)[-1]
    task_id = task[0]
    db.add_time(task_id, start_time, end_time, chat_id)
    bot.send_message(chat_id, "Время к задаче добавлено успешно!")


def edit_task(message):
    msg = bot.reply_to(message, "Введите номер задачи, которую хотите отредактировать:")
    bot.register_next_step_handler(msg, process_edit_step)


def process_edit_step(message):
    try:
        chat_id = message.chat.id
        task_id = int(message.text)
        task = db.get_task_by_id(task_id, chat_id)
        if task:
            bot.send_message(message, "Что вы хотите изменить?\n1. Описание\n2. Дату"
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
        response = category_list() + "\nВведите номер категории:"
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
