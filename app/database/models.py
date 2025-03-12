from sqlalchemy import BigInteger, String, ForeignKey, Boolean, DateTime, Text, VARCHAR
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from  sqlalchemy.ext.asyncio import  AsyncAttrs, async_sessionmaker, create_async_engine
from datetime import datetime

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3')

async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    p



class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)  # Уникальный идентификатор
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)  # ID пользователя в Telegram
    login: Mapped[str] = mapped_column(String(50), nullable=True)  # Логин (может быть пустым)
    name: Mapped[str] = mapped_column(String(50), nullable=True)  # Имя (может быть пустым)
    start_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())  # Дата начала
    is_trial: Mapped[bool] = mapped_column(Boolean, default=True)  # Тип (тест/платная)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)  # Дата окончания (может быть пустой)



class Category(Base):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))



class Category_recipe(Base):
    __tablename__ = 'category_recipes'
    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(BigInteger)
    recipe_id: Mapped[int] = mapped_column(BigInteger)


class Recipe(Base):
    __tablename__ = 'recipes'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(250))
    instructions: Mapped[str] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(BigInteger)  # Убедитесь, что это число
    type_id: Mapped[int] = mapped_column(BigInteger)  # Убедитесь, что это число
    cuisine_id: Mapped[int] = mapped_column(BigInteger)  # Убедитесь, что это число
    position: Mapped[int] = mapped_column(nullable=True)  # Может быть NULL
    like: Mapped[int] = mapped_column(nullable=True)  # Может быть NULL
    dislike: Mapped[int] = mapped_column(nullable=True)  # Может быть NULL

class Type_recipe(Base):
    __tablename__ = 'type_recipes'
    id: Mapped[int] = mapped_column(primary_key=True)
    type_id: Mapped[int] = mapped_column(BigInteger)
    recipe_id: Mapped[int] = mapped_column(BigInteger)

class Type(Base):
    __tablename__ = 'types'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))

class Cuisine(Base):
    __tablename__ = 'cuisines'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))


class Recipe_ingredient(Base):
    __tablename__ = 'recipe_ingredient'
    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(BigInteger)
    ingredient_id: Mapped[int] = mapped_column(BigInteger)


class Ingredient(Base):
    __tablename__ = 'ingredients'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))  # Название ингредиента
    protein: Mapped[str] = mapped_column(String(50))  # Белки
    fat: Mapped[str] = mapped_column(String(50))  # Жиры
    carbohydrate: Mapped[str] = mapped_column(String(50))  # Углеводы
    ingredient_type_id: Mapped[int] = mapped_column(ForeignKey('ingredient_type.id'))  # Ссылка на тип ингредиента

class IngredientType(Base):
    __tablename__ = 'ingredient_type'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))  # Название типа (например, "Мясо", "Рыба")

async def async_main():
    async with engine.begin() as conn:
        await  conn.run_sync(Base.metadata.create_all)