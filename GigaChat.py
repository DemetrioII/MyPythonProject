import os
import json
from dotenv import load_dotenv
import requests

# Загружаем токен из .env файла
load_dotenv()
TOKEN = os.getenv('GIGA-TOKEN')


class GigaChat:
    def __init__(self):
        self.base_url = 'https://api.giga.chat/v1/'
        self.headers = {
            'Authorization': f'Bearer {TOKEN}',
            'Content-Type': 'application/json',
        }

    # Метод для отправки сообщений
    def send_message(self, message_text):
        payload = {
            'message': message_text,
        }

        response = requests.post(
            f'{self.base_url}/messages',
            headers=self.headers,
            data=json.dumps(payload)
        )

        if response.status_code == 200:
            return response.json()['response']
        else:
            print(f"Ошибка: {response.text}")
            return None


def test():
    chatbot = GigaChat()
    while True:
        user_input = input("\nВведите сообщение (или введите 'exit', чтобы выйти): ")
        if user_input.lower() == 'exit':
            break
        answer = chatbot.send_message(user_input)
        print("Ответ:", answer)
