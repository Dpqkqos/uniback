from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import random
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from fastapi.middleware.cors import CORSMiddleware

# Настройка SQLite (база данных будет создана в файле database.db)
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Модели базы данных
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    middle_name = Column(String)
    birth_date = Column(String)
    birth_time = Column(String)
    registration_date = Column(DateTime, default=datetime.now)
    request = Column(String, default="Любовь")
    days_on_platform = Column(Integer, default=0)
    
    emotions = relationship("Emotion", back_populates="user")

class Emotion(Base):
    __tablename__ = "emotions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    state = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="emotions")

# Создание таблиц в базе данных (если их нет)
Base.metadata.create_all(bind=engine)

# Pydantic модели для валидации данных
class UserCreate(BaseModel):
    telegram_id: int
    last_name: str
    first_name: str
    middle_name: Optional[str] = None
    birth_date: str
    birth_time: str

class UserResponse(BaseModel):
    telegram_id: int
    first_name: str
    last_name: str
    middle_name: Optional[str]
    days_on_platform: int
    request: str

class EmotionCreate(BaseModel):
    telegram_id: int
    state: str

class EmotionResponse(BaseModel):
    id: int
    state: str
    created_at: datetime

# FastAPI приложение
app = FastAPI()

# Настройка CORS (чтобы фронтенд мог подключаться)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все домены
    allow_methods=["*"],  # Разрешить все методы (GET, POST и т.д.)
    allow_headers=["*"],  # Разрешить все заголовки
)

# Зависимость для работы с базой данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Вспомогательные функции
def calculate_days_since(date: datetime):
    return (datetime.now() - date).days

# Эндпоинты
@app.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.telegram_id == user.telegram_id).first()
    if db_user:
        raise HTTPException(status_code=400, detail="User already registered")
    
    new_user = User(
        telegram_id=user.telegram_id,
        first_name=user.first_name,
        last_name=user.last_name,
        middle_name=user.middle_name,
        birth_date=user.birth_date,
        birth_time=user.birth_time
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User registered successfully", "forecast": "Сегодня будет прекрасный день!"}

@app.get("/user/{telegram_id}")
def get_user(telegram_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "telegram_id": user.telegram_id,
        "fullName": f"{user.last_name} {user.first_name} {user.middle_name or ''}".strip(),
        "daysOnPlatform": calculate_days_since(user.registration_date),
        "request": user.request
    }

@app.get("/emotions/{telegram_id}")
def get_emotions(telegram_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return [
        {
            "id": emotion.id,
            "state": emotion.state,
            "created_at": emotion.created_at
        } for emotion in user.emotions
    ]

@app.post("/emotion/")
def create_emotion(emotion: EmotionCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == emotion.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_emotion = Emotion(
        user_id=user.id,
        state=emotion.state
    )
    
    db.add(new_emotion)
    db.commit()
    db.refresh(new_emotion)
    
    return {"message": "Emotion added successfully"}

@app.delete("/emotion/{emotion_id}")
def delete_emotion(emotion_id: int, db: Session = Depends(get_db)):
    emotion = db.query(Emotion).filter(Emotion.id == emotion_id).first()
    if not emotion:
        raise HTTPException(status_code=404, detail="Emotion not found")
    
    db.delete(emotion)
    db.commit()
    
    return {"message": "Emotion deleted successfully"}

@app.get("/forecast/{telegram_id}")
def get_forecast(telegram_id: int):
    forecasts = [
        "Сегодня вас ждут приятные сюрпризы!",
        "Время проявить инициативу в важных делах",
        "Ожидайте неожиданных встреч",
        "Будьте внимательны к деталям",
        "Идеальный день для новых начинаний"
    ]
    return {"forecast": random.choice(forecasts)}
