from sqlalchemy.ext.asyncio import AsyncSession, async_session
from typing import List, Optional
from sqlalchemy import select, delete, func
from datetime import datetime, timedelta
from app.database.models import User, Recipe, Recipe_ingredient, Ingredient, Category, Cuisine, Type, IngredientType


async def set_user(tg_id: int, is_trial: bool = True) -> User:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            user = User(tg_id=tg_id, is_trial=is_trial, start_date=datetime.now(), end_date=datetime.now() + timedelta(days=3))
            session.add(user)
            await session.commit()
        return user

async def get_user(tg_id: int) -> Optional[User]:
    async with async_session() as session:
        return await session.scalar(select(User).where(User.tg_id == tg_id))

async def create_user(tg_id: int, login: str, name: str, is_trial: bool = True) -> User:
    async with async_session() as session:
        user = User(tg_id=tg_id, login=login, name=name, is_trial=is_trial, start_date=datetime.now(), end_date=datetime.now() + timedelta(days=3 if is_trial else 365))
        session.add(user)
        await session.commit()
        return user

async def get_ingredients_by_type(type_name: str, session: AsyncSession) -> List[str]:
    type_query = select(IngredientType.id).where(IngredientType.name == type_name)
    type_result = await session.execute(type_query)
    type_id = type_result.scalar()
    if not type_id:
        raise ValueError(f"Тип '{type_name}' не найден.")
    ingredients_query = select(Ingredient.name).where(Ingredient.ingredient_type_id == type_id)
    ingredients_result = await session.execute(ingredients_query)
    return [row[0] for row in ingredients_result]

async def get_or_create_ingredient(session: AsyncSession, name: str) -> Ingredient:
    ingredient = await session.scalar(select(Ingredient).where(Ingredient.name == name))
    if not ingredient:
        ingredient = Ingredient(name=name)
        session.add(ingredient)
        await session.commit()
    return ingredient

async def get_or_create_category(session: AsyncSession, name: str) -> Category:
    category = await session.scalar(select(Category).where(Category.name == name))
    if not category:
        category = Category(name=name)
        session.add(category)
        await session.commit()
    return category

async def get_or_create_type(session: AsyncSession, name: str) -> Type:
    type_ = await session.scalar(select(Type).where(Type.name == name))
    if not type_:
        type_ = Type(name=name)
        session.add(type_)
        await session.commit()
    return type_

async def get_or_create_cuisine(session: AsyncSession, name: str) -> Cuisine:
    cuisine = await session.scalar(select(Cuisine).where(Cuisine.name == name))
    if not cuisine:
        cuisine = Cuisine(name=name)
        session.add(cuisine)
        await session.commit()
    return cuisine

async def search_recipes(session: AsyncSession, selected_diet: Optional[str], selected_categorys: Optional[str], selected_country: Optional[str], selected_ingridients: List[str], is_trial: bool) -> List[Recipe]:
    query = select(Recipe)
    if selected_categorys and selected_categorys.lower() != "не важно":
        category_query = select(Category.id).where(Category.name == selected_categorys)
        category_result = await session.execute(category_query)
        category_id = category_result.scalar()
        if category_id:
            query = query.where(Recipe.category_id == category_id)
    if selected_country and selected_country.lower() != "не важно":
        cuisine_query = select(Cuisine.id).where(Cuisine.name == selected_country)
        cuisine_result = await session.execute(cuisine_query)
        cuisine_id = cuisine_result.scalar()
        if cuisine_id:
            query = query.where(Recipe.cuisine_id == cuisine_id)
    if selected_diet and selected_diet.lower() != "не важно":
        diet_query = select(Type.id).where(Type.name == selected_diet)
        diet_result = await session.execute(diet_query)
        diet_id = diet_result.scalar()
        if diet_id:
            query = query.where(Recipe.type_id == diet_id)
    if selected_ingridients:
        ingredients_query = select(Ingredient.id).where(Ingredient.name.in_(selected_ingridients))
        ingredients_result = await session.execute(ingredients_query)
        ingredient_ids = [ing[0] for ing in ingredients_result]
        if ingredient_ids:
            query = query.join(Recipe_ingredient, Recipe.id == Recipe_ingredient.recipe_id).where(
                Recipe_ingredient.ingredient_id.in_(ingredient_ids))
    query = query.order_by(func.random())
    result = await session.execute(query)
    recipes = result.scalars().all()
    return recipes[:3] if is_trial else recipes[:10]

async def update_user_access(tg_id: int) -> bool:
    async with async_session() as session:
        user = await get_user(tg_id)
        if user:
            user.is_trial = False
            user.end_date = datetime.now() + timedelta(days=365)
            await session.commit()
            return True
        return False

async def add_recipe(session: AsyncSession, title: str, instructions: str, category_name: str, type_name: str, cuisine_name: str, selected_ingredients: List[str]) -> Recipe:
    category = await get_or_create_category(session, category_name)
    type_ = await get_or_create_type(session, type_name)
    cuisine = await get_or_create_cuisine(session, cuisine_name)
    recipe = Recipe(
        title=title,
        instructions=instructions,
        category_id=category.id,
        type_id=type_.id,
        cuisine_id=cuisine.id,
        position=None,
        like=None,
        dislike=None
    )
    session.add(recipe)
    await session.commit()
    await session.refresh(recipe)
    for ingredient_name in selected_ingredients:
        ingredient = await get_or_create_ingredient(session, ingredient_name)
        recipe_ingredient = Recipe_ingredient(recipe_id=recipe.id, ingredient_id=ingredient.id)
        session.add(recipe_ingredient)
    await session.commit()
    return recipe

async def update_recipe(session: AsyncSession, recipe_id: int, title: str, instructions: str, category_name: str, type_name: str, cuisine_name: str, selected_ingredients: List[str]) -> Recipe:
    recipe = await session.scalar(select(Recipe).where(Recipe.id == recipe_id))
    if not recipe:
        raise ValueError(f"Рецепт с ID {recipe_id} не найден.")
    category = await get_or_create_category(session, category_name)
    type_ = await get_or_create_type(session, type_name)
    cuisine = await get_or_create_cuisine(session, cuisine_name)
    recipe.title = title
    recipe.instructions = instructions
    recipe.category_id = category.id
    recipe.type_id = type_.id
    recipe.cuisine_id = cuisine.id
    await session.execute(delete(Recipe_ingredient).where(Recipe_ingredient.recipe_id == recipe.id))
    for ingredient_name in selected_ingredients:
        ingredient = await get_or_create_ingredient(session, ingredient_name)
        recipe_ingredient = Recipe_ingredient(recipe_id=recipe.id, ingredient_id=ingredient.id)
        session.add(recipe_ingredient)
    await session.commit()
    return recipe

async def delete_recipe(recipe_id: int) -> bool:
    async with async_session() as session:
        recipe = await session.scalar(select(Recipe).where(Recipe.id == recipe_id))
        if recipe:
            await session.delete(recipe)
            await session.commit()
            return True
        return False