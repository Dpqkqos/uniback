from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import g4f
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение к базе данных
DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Модель пользователя
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    last_name = Column(String)
    first_name = Column(String)
    middle_name = Column(String, nullable=True)
    birth_date = Column(String)
    birth_time = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    request = Column(String, default="Любовь")
    avatar_url = Column(String, nullable=True)  # Добавляем поле для аватарки

# Модель эмоций
class Emotion(Base):
    __tablename__ = "emotions"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, index=True)
    state = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# Создание таблиц
Base.metadata.create_all(bind=engine)

# Pydantic схемы
class UserCreate(BaseModel):
    telegram_id: int
    last_name: str
    first_name: str
    middle_name: Optional[str] = ""
    birth_date: str
    birth_time: str
    avatar_url: Optional[str] = None  # Добавляем поле для аватарки

class EmotionCreate(BaseModel):
    telegram_id: int
    state: str

class UserUpdateRequest(BaseModel):
    telegram_id: int
    request: str

# Регистрация пользователя
@app.post("/register")
def register_user(user: UserCreate):
    db = SessionLocal()
    existing_user = db.query(User).filter(User.telegram_id == user.telegram_id).first()
    if existing_user:
        db.close()
        raise HTTPException(status_code=400, detail="Пользователь уже зарегистрирован")
    new_user = User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.close()
    return {"message": "Пользователь зарегистрирован"}

# Получение данных пользователя
@app.get("/user/{telegram_id}")
def get_user(telegram_id: int):
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    db.close()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user

# Добавление эмоции
@app.post("/add_emotion")
def add_emotion(emotion: EmotionCreate):
    db = SessionLocal()
    new_emotion = Emotion(**emotion.dict())
    db.add(new_emotion)
    db.commit()
    db.refresh(new_emotion)
    db.close()
    return new_emotion

# Получение эмоций пользователя
@app.get("/emotions/{telegram_id}", response_model=List[EmotionCreate])
def get_emotions(telegram_id: int):
    db = SessionLocal()
    emotions = db.query(Emotion).filter(Emotion.telegram_id == telegram_id).all()
    db.close()
    return emotions

# Обновление запроса пользователя
@app.post("/update_request")
def update_request(request_data: UserUpdateRequest):
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == request_data.telegram_id).first()
    if not user:
        db.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.request = request_data.request
    db.commit()
    db.close()
    return {"message": "Запрос обновлен"}

# Генерация прогноза на основе данных пользователя
@app.get("/forecast/{telegram_id}")
def generate_forecast(telegram_id: int):
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    db.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    prompt = f"Сгенерируй астрологический прогноз на день для человека с именем {user.first_name} {user.last_name}, родившегося {user.birth_date} в {user.birth_time}."
    
    try:
        forecast = g4f.ChatCompletion.create(
            model=g4f.models.default,
            messages=[{"role": "user", "content": prompt}]
        )
        return {"forecast": forecast}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации прогноза: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
