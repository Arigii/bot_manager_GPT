import requests
import logging  # модуль для сбора логов

# подтягиваем константы из config файла
from config import LOGS, GPT_URL, SYSTEM_PORMPT
from creds import get_creds  # модуль для получения токенов

# настраиваем запись логов в файл
logging.basicConfig(filename=LOGS, level=logging.INFO,
                    format="%(asctime)s FILE: %(filename)s IN: %(funcName)s MESSAGE: %(message)s", filemode="w")


# запрос к GPT
def ask_gpt(messages):
    IAM_TOKEN, FOLDER_ID = get_creds()  # получаем iam_token и folder_id из файлов

    gpt_headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
        'Content-Type': 'application/json'
    }

    # Создаем базовое сообщение с системным prompt
    message_payload = SYSTEM_PORMPT
    message_payload.append({'role': 'user', 'text': messages})

    data = {
        'modelUri': f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": 500
        },
        "messages": message_payload
    }

    try:
        response = requests.post(GPT_URL, headers=gpt_headers, json=data)
        response_data = response.json()
        logging.info(f"GPT Response: {response_data}")

        if response.status_code != 200:
            return False, f"Ошибка GPT. Статус-код: {response.status_code}"
        answer = response.json()['result']['alternatives'][0]['message']['text']
        return True, answer
    except Exception as e:
        logging.error(f"Ошибка подключеня к GPT: {e}")
        return False, "Ошибка при обращении к GPT"
