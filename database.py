import sqlite3
import threading


class Database:
    def __init__(self, db_name="users_tasks.db"):
        self.db_lock = threading.Lock()
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY,
                                chat_id TEXT UNIQUE
                              )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
                                            id INTEGER PRIMARY KEY,
                                            user_id INTEGER,
                                            sequence_number INTEGER,
                                            task TEXT,
                                            date DATE,
                                            start_time TEXT,
                                            end_time TEXT,
                                            reminder TEXT,
                                            FOREIGN KEY (user_id) REFERENCES users (id)
                                          )''')
            self.conn.commit()

    def add_user(self, chat_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO users (chat_id) VALUES (?)", (chat_id,))
            self.conn.commit()

    def add_task(self, user_id, task, reminder=None):
        with self.db_lock:
            cursor = self.conn.cursor()
            # Получаем максимальный sequence_number для данного пользователя
            cursor.execute("SELECT MAX(sequence_number) FROM tasks WHERE user_id=?", (user_id,))
            max_sequence_number = cursor.fetchone()[0]
            if max_sequence_number is None:
                sequence_number = 1
            else:
                sequence_number = max_sequence_number + 1
            cursor.execute("INSERT INTO tasks (user_id, sequence_number, task, reminder) VALUES (?, ?, ?, ?)",
                           (user_id, sequence_number, task, reminder))
            self.conn.commit()

    def update_list(self, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            # Получаем все задачи пользователя, отсортированные по времени добавления
            cursor.execute("SELECT id FROM tasks WHERE user_id=? ORDER BY id", (user_id,))
            tasks = cursor.fetchall()
            # Обновляем sequence_number для каждой задачи в порядке добавления
            for index, task_id in enumerate(tasks, start=1):
                cursor.execute("UPDATE tasks SET sequence_number=? WHERE id=?", (index, task_id[0]))
            self.conn.commit()

    def add_date(self, task_id, date):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET date=? WHERE id=?", (date, task_id))
            self.conn.commit()

    def update_date(self, sequence_number, date):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET date=? WHERE sequence_number=?", (date, sequence_number))
            self.conn.commit()

    def add_time(self, task_id, start_time, end_time):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET start_time=?, end_time=? WHERE id=?", (start_time, end_time, task_id))
            self.conn.commit()

    def update_task(self, sequence_number, new_task):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET task=? WHERE sequence_number=?", (new_task, sequence_number))
            self.conn.commit()

    def update_task_start_time(self, sequence_number, start_time):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET start_time=? WHERE sequence_number=?", (start_time, sequence_number))
            self.conn.commit()

    def update_task_end_time(self, sequence_number, end_time):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET end_time=? WHERE sequence_number=?", (end_time, sequence_number))
            self.conn.commit()

    def get_task_by_id(self, sequence_number):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE sequence_number=?", (sequence_number,))
            return cursor.fetchone()

    def get_tasks(self, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY id", (user_id,))
            return cursor.fetchall()

    def delete_task(self, sequence_number):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE sequence_number=?", (sequence_number,))
            self.conn.commit()

    def delete_remind(self, reminder, user_id):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET reminder=? WHERE user_id=?", (reminder, user_id))
            self.conn.commit()

    def set_reminder(self, sequence_number, reminder):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE tasks SET reminder=? WHERE sequence_number=?", (reminder, sequence_number))
            self.conn.commit()

    def get_all_tasks_with_reminders(self):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE reminder IS NOT NULL")
            return cursor.fetchall()

    def get_all_datatime(self):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT user_id, task, date, start_time, end_time, reminder FROM tasks WHERE date IS NOT NULL "
                           "AND start_time IS NOT NULL AND end_time IS NOT NULL")
            return cursor.fetchall()
