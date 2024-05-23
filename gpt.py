import requests
import logging  # модуль для сбора логов
# подтягиваем константы из config файла
from config import LOGS
from creds import get_creds  # модуль для получения токенов

# настраиваем запись логов в файл
logging.basicConfig(filename=LOGS, level=logging.INFO,
                    format="%(asctime)s FILE: %(filename)s IN: %(funcName)s MESSAGE: %(message)s", filemode="w")

IAM_TOKEN, FOLDER_ID = get_creds()  # получаем iam_token и folder_id из файлов


# запрос к GPT
def ask_gpt(messages):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
        'Content-Type': 'application/json'
    }

    # Создаем базовое сообщение с системным prompt
    message_payload = [{'role': 'system',
                        'text': 'Ты помощник в тайм-менеджере. Не'
                                'Необходимо дать рекомендация и предложения. '
                                'Не объясняй пользователю, что ты умеешь и можешь. '
                                'Отвечай строго не больше 3-4 предложений без пояснений'}]

    # Добавляем пользовательские сообщения
    if isinstance(messages, list):
        for msg in messages:
            message_payload.append({'role': 'user', 'text': msg})
    else:
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
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()
        logging.info(f"GPT Response: {response_data}")

        if response.status_code != 200:
            return False, f"Ошибка GPT. Статус-код: {response.status_code}"
        answer = response.json()['result']['alternatives'][0]['message']['text']
        return True, answer
    except Exception as e:
        logging.error(e)
        return False, "Ошибка при обращении к GPT"
