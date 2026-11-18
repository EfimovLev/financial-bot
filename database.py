from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, DateTime, BigInteger

DB_URL = "sqlite+aiosqlite:///finance.db"

engine = create_async_engine(DB_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    balance: Mapped[float] = mapped_column(Float, default=0.0)

class Category(Base):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)  # 'income' или 'expense'
    user_id: Mapped[int] = mapped_column(BigInteger)

class Transaction(Base):
    __tablename__ = 'transactions'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    amount: Mapped[float] = mapped_column(Float)
    type: Mapped[str] = mapped_column(String) # 'income' или 'expense'
    category: Mapped[str] = mapped_column(String)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_or_create_user(session: AsyncSession, telegram_id: int) -> User:
    user = await session.get(User, telegram_id)
    if not user:
        user = User(telegram_id=telegram_id, balance=0.0)
        session.add(user)
        
        # Предустановленные базовые категории (без Фриланса и Подарков)
        defaults = [
            ("Продукты", "expense"), ("Транспорт", "expense"),
            ("Жилье", "expense"), ("Развлечения", "expense"), ("Кафе", "expense"),
            ("Зарплата", "income")
        ]
        for name, ctype in defaults:
            cat = Category(name=name, type=ctype, user_id=telegram_id)
            session.add(cat)
            
        await session.commit()
        await session.refresh(user)
    return user
