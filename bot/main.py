#интейк ботик на айограм - будет вынимать сообщения и создавать инцы через рест

import os
import re
from typing import Optional, Set

import httpx
from pydantic import BaseModel
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

#Settings
class Settings(BaseModel):
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str  # можно несколько ID через запятую
    API_URL: str = "http://api:8000" #имя сервиса апи внутри docker-compose
    API_KEY: Optional[str] = None

def get_settings() -> Settings:
    #тащим значения из енв - компоуз прокинет из енв
    return Settings(
        TELEGRAM_BOT_TOKEN=os.environ["TELEGRAM_BOT_TOKEN"],
        TELEGRAM_CHAT_ID=os.environ["TELEGRAM_CHAT_ID"],
        API_URL=os.environ.get("API_URL", "http://api:8000"),
        API_KEY=os.environ.get("API_KEY"),
    )

S = get_settings()
bot = Bot(S.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
#фильтр по чатам чтобы не спамить все входящие 
ALLOWED_CHAT_IDS: Set[int] = {int(x) for x in S.TELEGRAM_CHAT_ID.split(",")}

# парсинг источника 
SOURCE_RE = re.compile(
    r"(?:^\[(?P<tag>operator|monitoring|partner)\]\s*)|(?:\bsource=(?P<kv>operator|monitoring|partner)\b)",
    re.IGNORECASE,
)

def extract_source_and_description(text: str):
    source = "operator"
    m = SOURCE_RE.search(text or "")
    if m:
        picked = (m.group("tag") or m.group("kv") or "").lower()
        if picked in {"operator", "monitoring", "partner"}:
            source = picked
        #убираем маркер источника из описания чтобы не засорять
        text = SOURCE_RE.sub("", text).strip(" -|")
    return source, (text or "").strip()

#вызовы API 
async def api_create_incident(description: str, source: str, idempotency_key: str) -> dict:
    headers = {"Content-Type": "application/json", "X-Idempotency-Key": idempotency_key}
    if S.API_KEY:
        headers["X-API-Key"] = S.API_KEY
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{S.API_URL}/api/v1/incidents", json={"description": description, "source": source}, headers=headers)
        r.raise_for_status()
        return r.json()

async def api_update_status(incident_id: int, status: str) -> dict:
    headers = {"Content-Type": "application/json"}
    if S.API_KEY:
        headers["X-API-Key"] = S.API_KEY
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.patch(
            f"{S.API_URL}/api/v1/incidents/{incident_id}",
            json={"status": status},   # можно добавить description_append при желании
            headers=headers,
        )
        r.raise_for_status()
        return r.json()

#handlers 
@dp.message(Command("start"))
async def on_start(message: Message):
    if message.chat.id not in ALLOWED_CHAT_IDS:
        return
    await message.reply(
        "Бот готов. Пришлите инцидент в формате:\n"
        "1) [monitoring] Самокат #42 оффлайн\n"
        "2) Самокат #42 оффлайн | source=partner\n"
        "Или используйте /update <id> <status>"
    )

@dp.message(Command("update"))
async def on_update(message: Message):
    if message.chat.id not in ALLOWED_CHAT_IDS:
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.reply("Использование: /update <id> <status>")
        return
    try:
        inc_id = int(parts[1]); new_status = parts[2].upper()
        data = await api_update_status(inc_id, new_status)
        await message.reply(f"✅ Обновлён инцидент #{data['id']}: {data['status']}")
    except Exception as e:
        await message.reply(f"❌ Ошибка обновления: {e}")

@dp.message(F.text)
async def on_message(message: Message):
    if message.chat.id not in ALLOWED_CHAT_IDS:
        return
    try:
        source, description = extract_source_and_description(message.text)
        if not description:
            await message.reply("Текст инцидента пустой. Добавьте описание.")
            return
        idem = f"tg:{message.chat.id}:{message.message_id}"
        data = await api_create_incident(description, source, idem)
        await message.reply(f"✅ Инцидент создан: #{data['id']} ({data['status']})")
    except httpx.HTTPStatusError as e:
        await message.reply(f"❌ API ошибка: {e.response.status_code} {e.response.text}")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    #для простоты-polling, на проде можно перейти на вебхук
    dp.run_polling(bot)
