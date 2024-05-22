import telebot
from config import TOKEN
from database import Database
import datetime

bot = telebot.TeleBot(TOKEN)
db = Database()


def validate_date(date):
    try:
        datetime.datetime.strptime(date, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validate_time(time_set):
    try:
        datetime.datetime.strptime(time_set, '%H:%M')
        return True
    except ValueError:
        return False
