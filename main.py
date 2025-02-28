from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import g4f
import logging
from fastapi.middleware.cors import CORSMiddleware

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Разрешение CORS (для работы с фронтендом)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все источники (можно указать конкретные)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модель данных для регистрации
class RegistrationData(BaseModel):
    telegram_id: int  # Идентификатор пользователя в Telegram
    lastName: str
    firstName: str
    middleName: str
    birthDate: str  # Формат: "YYYY-MM-DD"
    birthTime: str  # Формат: "HH:MM"

# Модель данных для запроса
class UserRequest(BaseModel):
    telegram_id: int
    request: str  # Например, "Любовь", "Карьера" и т.д.

# Модель данных для эмоции
class UserEmotion(BaseModel):
    telegram_id: int
    state: str  # Описание эмоции

# Подключение к базе данных
def get_db_connection():
    conn = sqlite3.connect('app.db')
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
            telegram_id INTEGER UNIQUE,
            last_name TEXT,
            first_name TEXT,
            middle_name TEXT,
            birth_date DATE,
            birth_time TIME,
            forecast TEXT,
            avatar_url TEXT
        )
    ''')

    # Создание таблицы запросов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            request TEXT,
            FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
        )
    ''')

    # Создание таблицы эмоций
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_emotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            state TEXT,
            FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
        )
    ''')

    conn.commit()
    conn.close()

# Инициализация базы данных при запуске
init_db()

# Маршрут для регистрации
@app.post("/register")
async def register_user(data: RegistrationData):
    try:
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

# Маршрут для обновления запроса пользователя
@app.post("/update_request")
async def update_request(request_data: UserRequest):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Сохраняем запрос в базу данных
        cursor.execute('''
            INSERT INTO user_requests (telegram_id, request)
            VALUES (?, ?)
        ''', (request_data.telegram_id, request_data.request))
        conn.commit()
        conn.close()

        logger.info(f"Запрос пользователя {request_data.telegram_id} успешно обновлен.")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Ошибка при обновлении запроса: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при обновлении запроса")

# Маршрут для добавления эмоции
@app.post("/add_emotion")
async def add_emotion(emotion_data: UserEmotion):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Сохраняем эмоцию в базу данных
        cursor.execute('''
            INSERT INTO user_emotions (telegram_id, state)
            VALUES (?, ?)
        ''', (emotion_data.telegram_id, emotion_data.state))
        conn.commit()
        conn.close()

        logger.info(f"Эмоция пользователя {emotion_data.telegram_id} успешно добавлена.")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Ошибка при добавлении эмоции: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при добавлении эмоции")

# Маршрут для получения эмоций пользователя
@app.get("/emotions/{telegram_id}")
async def get_emotions(telegram_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Получаем все эмоции пользователя
        cursor.execute('SELECT * FROM user_emotions WHERE telegram_id = ?', (telegram_id,))
        emotions = cursor.fetchall()
        conn.close()

        if not emotions:
            logger.warning(f"Эмоции для пользователя с telegram_id={telegram_id} не найдены.")
            return {"emotions": []}

        return {"emotions": [dict(emotion) for emotion in emotions]}
    except Exception as e:
        logger.error(f"Ошибка при получении эмоций: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при получении эмоций")

# Маршрут для обновления данных пользователя (аватарка и имя)
@app.post("/update_user")
async def update_user(telegram_id: int, full_name: str, avatar_url: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Обновляем данные пользователя
        cursor.execute('''
            UPDATE users
            SET first_name = ?, last_name = ?, avatar_url = ?
            WHERE telegram_id = ?
        ''', (full_name.split()[0], full_name.split()[1], avatar_url, telegram_id))
        conn.commit()
        conn.close()

        logger.info(f"Данные пользователя {telegram_id} успешно обновлены.")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Ошибка при обновлении данных пользователя: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при обновлении данных пользователя")

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
async def get_forecast(telegram_id: int):
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
    uvicorn.run(app, host="127.0.0.1", port=8000)
