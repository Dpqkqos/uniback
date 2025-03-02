from fastapi import FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from datetime import datetime

# Настройка базы данных
engine = create_async_engine("sqlite+aiosqlite:///db.sqlite3", echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Модель для регистрации
class RegistrationData(BaseModel):
    tg_id: int
    surname: str
    name: str
    patronymic: str
    birth_date: str
    birth_time: str

app = FastAPI()

@app.get("/api/main/{tg_id}")
async def check_registration(tg_id: int):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        
        if user:
            return {"isregistred": user.isregistred}
        else:
            return {"isregistred": False}

@app.post("/api/register")
async def register_user(data: RegistrationData):
    async with async_session() as session:
        # Проверяем, существует ли пользователь
        result = await session.execute(select(User).where(User.tg_id == data.tg_id))
        user = result.scalar_one_or_none()

        if user:
            # Если пользователь существует, обновляем его данные
            user.surname = data.surname
            user.name = data.name
            user.patronymic = data.patronymic
            user.birth_date = data.birth_date
            user.birth_time = data.birth_time
            user.isregistred = True
        else:
            # Если пользователь не существует, создаем нового
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

        await session.commit()
        return {"status": "success", "isregistred": True}
