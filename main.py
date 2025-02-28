from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import g4f
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class RegistrationData(BaseModel):
    telegram_id: int
    lastName: str
    firstName: str
    middleName: str
    birthDate: str
    birthTime: str

def get_db_connection():
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            last_name TEXT,
            first_name TEXT,
            middle_name TEXT,
            birth_date DATE,
            birth_time TIME,
            forecast TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.post("/register")
async def register_user(data: RegistrationData):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (data.telegram_id,))
        existing_user = cursor.fetchone()

        if existing_user:
            logger.info(f"Пользователь с telegram_id={data.telegram_id} уже зарегистрирован")
            return {"forecast": existing_user["forecast"]}

        def generate_forecast(data: RegistrationData):
            prompt = (
                f"Пользователь: {data.lastName} {data.firstName} {data.middleName}\n"
                f"Дата рождения: {data.birthDate}\n"
                f"Время рождения: {data.birthTime}\n"
                "Сгенерируй прогноз на день."
            )
            try:
                response = g4f.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                return response
            except Exception as e:
                logger.error(f"Ошибка генерации прогноза: {e}")
                return "Сегодня будет прекрасный день! Желаю вам удачи!"

        forecast = generate_forecast(data)
        
        cursor.execute('''
            INSERT INTO users (telegram_id, last_name, first_name, middle_name, birth_date, birth_time, forecast)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data.telegram_id, data.lastName, data.firstName, data.middleName, data.birthDate, data.birthTime, forecast))
        conn.commit()
        conn.close()
        return {"forecast": forecast}
    except Exception as e:
        logger.error(f"Ошибка регистрации: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при регистрации пользователя")

@app.get("/forecast/{telegram_id}")
async def get_forecast(telegram_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        return {"forecast": user["forecast"]}
    except Exception as e:
        logger.error(f"Ошибка получения прогноза: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при получении прогноза")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
