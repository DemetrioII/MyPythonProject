from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
import os
from dotenv import load_dotenv
from fastapi import FastAPI

parser = StrOutputParser()

app = FastAPI()


load_dotenv()
TOKEN = os.getenv('GIGA-TOKEN')

model = GigaChat(
    credentials=TOKEN,
    scope="GIGACHAT_API_PERS",
    model="GigaChat",
    verify_ssl_certs=False,
)


@app.get("/gigachat", tags = ["Анализ через LLM"])
async def get_llm_analysis():
    # Подгрузка промпта
    with open("prompt.txt", "r", encoding="UTF-8") as f :
        system_message = f.read()
    # Тут лолжна быть подгрузка json из бд
    with open("parced_data.json", "r", encoding="UTF-8") as f:
        data = f.read()

    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=data),
    ]

    result = model.invoke(messages)

    # Должно загружаться в бд
    summary = parser.invoke(result)
    return summary

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("GigaChat:app", host="127.0.0.1", port=5173, reload=True)