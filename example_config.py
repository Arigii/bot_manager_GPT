HOME_DIR = '**path_to_the_project**'  # путь к папке с проектом

LOGS = f'{HOME_DIR}/logs.txt'  # файл для логов
DB_FILE = f'{HOME_DIR}/users_tasks.db'  # файл для базы данных

IAM_TOKEN_PATH = f'{HOME_DIR}/creds/iam_token.txt'  # файл для хранения iam_token
FOLDER_ID_PATH = f'{HOME_DIR}/creds/folder_id.txt'  # файл для хранения folder_id
BOT_TOKEN_PATH = f'{HOME_DIR}/creds/bot_token.txt'  # файл для хранения bot_token

# Константы для запроса к GPT
GPT_URL = "**url_gpt**"

SYSTEM_PORMPT = [{'role': 'system',
                  'text': '**system_prompt_text**'}]
