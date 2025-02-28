from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import g4f
import logging
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все домены
    allow_methods=["*"],  # Разрешить все методы
    allow_headers=["*"],  # Разрешить все заголовки
)

# Получаем путь к базе данных из переменной окружения
DATABASE_PATH = os.getenv("DATABASE_PATH", "app.db")  # По умолчанию 'app.db'

# Модель данных для регистрации
class RegistrationData(BaseModel):
    telegram_id: str  # Идентификатор пользователя в Telegram
    lastName: str
    firstName: str
    middleName: str
    birthDate: str  # Формат: "YYYY-MM-DD"
    birthTime: str  # Формат: "HH:MM"

# Подключение к базе данных
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)  # Используем DATABASE_PATH
    conn.row_factory = sqlite3.Row
    return conn

# Инициализация базы данных
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Создание таблицы пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT UNIQUE,
            last_name TEXT,
            first_name TEXT,
            middle_name TEXT,
            birth_date TEXT,
            birth_time TEXT,
            forecast TEXT
        )
    ''')

    conn.commit()
    conn.close()

# Инициализация базы данных при запуске
init_db()

# Корневой маршрут
@app.get("/")
async def root():
    return {"message": "Welcome to the Forecast API!"}

# Маршрут для регистрации
@app.post("/register")
async def register_user(data: RegistrationData):
    try:
        # Логируем входящие данные
        logger.info(f"Received data: {data}")

        # Проверяем, существует ли пользователь с таким telegram_id
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (data.telegram_id,))
        existing_user = cursor.fetchone()

        if existing_user:
            logger.info(f"Пользователь с telegram_id={data.telegram_id} уже зарегистрирован.")
            return {"forecast": existing_user["forecast"]}

        # Генерация прогноза на основе данных
        forecast = generate_forecast(data)

        # Сохранение данных пользователя в базу данных
        cursor.execute('''
            INSERT INTO users (telegram_id, last_name, first_name, middle_name, birth_date, birth_time, forecast)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data.telegram_id, data.lastName, data.firstName, data.middleName, data.birthDate, data.birthTime, forecast))
        conn.commit()
        conn.close()

        logger.info(f"Пользователь {data.firstName} {data.lastName} успешно зарегистрирован.")
        return {"forecast": forecast}
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при регистрации пользователя")

# Функция для генерации прогноза
def generate_forecast(data: RegistrationData):
    try:
        # Формируем запрос для GPT
        prompt = (
            f"Пользователь: {data.lastName} {data.firstName} {data.middleName}\n"
            f"Дата рождения: {data.birthDate}\n"
            f"Время рождения: {data.birthTime}\n"
            "Сгенерируй прогноз на день."
        )

        # Используем g4f для генерации прогноза
        response = g4f.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )

        return response
    except Exception as e:
        logger.error(f"Ошибка при генерации прогноза: {e}")
        return "Сегодня будет прекрасный день! Желаю вам удачи!"

# Маршрут для получения прогноза по telegram_id
@app.get("/forecast/{telegram_id}")
async def get_forecast(telegram_id: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT forecast FROM users WHERE telegram_id = ?', (telegram_id,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            logger.warning(f"Пользователь с telegram_id={telegram_id} не найден.")
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        return {"forecast": result["forecast"]}
    except Exception as e:
        logger.error(f"Ошибка при получении прогноза: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при получении прогноза")

# Запуск сервера
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))  # Используем порт из переменной окружения или 8000 по умолчанию
    uvicorn.run(app, host="0.0.0.0", port=port)
