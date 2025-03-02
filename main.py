from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import ForeignKey, String, BigInteger, Date, Time, select
from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from pydantic import BaseModel
from datetime import datetime

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3', echo=True)
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    isregistred: Mapped[bool] = mapped_column(default=False)
    surname: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(50))
    patronymic: Mapped[str] = mapped_column(String(50))
    birth_date: Mapped[str] = mapped_column(Date)
    birth_time: Mapped[str] = mapped_column(Time)
    request: Mapped[str] = mapped_column(String(100), default="Любовь")

class Emotion(Base):
    __tablename__ = 'emotion'

    id: Mapped[int] = mapped_column(primary_key=True)
    emotion: Mapped[str] = mapped_column(String(256))
    user: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

class RegistrationData(BaseModel):
    tg_id: int
    surname: str
    name: str
    patronymic: str
    birth_date: str
    birth_time: str

@asynccontextmanager
async def lifespan(app_: FastAPI):
    await init_db()
    yield

app = FastAPI(title="UNI!", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/main/{tg_id}")
async def check_registration(tg_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            return {"isregistred": False}
        return {"isregistred": user.isregistred}

@app.post("/api/register")
async def register_user(data: RegistrationData):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == data.tg_id))
        
        if not user:
            # Создаем нового пользователя
            new_user = User(
                tg_id=data.tg_id,
                surname=data.surname,
                name=data.name,
                patronymic=data.patronymic,
                birth_date=data.birth_date,
                birth_time=data.birth_time,
                isregistred=True
            )
            session.add(new_user)
        else:
            # Обновляем существующего
            user.surname = data.surname
            user.name = data.name
            user.patronymic = data.patronymic
            user.birth_date = data.birth_date
            user.birth_time = data.birth_time
            user.isregistred = True
        
        await session.commit()
        return {"status": "success", "isregistred": True}

@app.get("/api/user/{tg_id}")
async def get_user_info(tg_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "id": user.id,
            "tg_id": user.tg_id,
            "full_name": f"{user.surname} {user.name} {user.patronymic}",
            "birth_date": user.birth_date,
            "birth_time": user.birth_time,
            "request": user.request
        }

@app.post("/api/update_request/{tg_id}")
async def update_request(tg_id: int, request: str):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.request = request
        await session.commit()
        return {"status": "success"}

@app.get("/api/emotions/{tg_id}")
async def get_emotions(tg_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        emotions = await session.scalars(select(Emotion).where(Emotion.user == user.id))
        return [{"id": e.id, "emotion": e.emotion} for e in emotions]

@app.post("/api/add_emotion/{tg_id}")
async def add_emotion(tg_id: int, emotion: str):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        new_emotion = Emotion(emotion=emotion, user=user.id)
        session.add(new_emotion)
        await session.commit()
        return {"status": "success", "emotion_id": new_emotion.id}

@app.delete("/api/delete_emotion/{emotion_id}")
async def delete_emotion(emotion_id: int):
    async with async_session() as session:
        emotion = await session.scalar(select(Emotion).where(Emotion.id == emotion_id))
        if not emotion:
            raise HTTPException(status_code=404, detail="Emotion not found")
        
        await session.delete(emotion)
        await session.commit()
        return {"status": "success"}
