import re
from datetime import datetime, timedelta
from typing import List, Optional

from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select, and_, or_, func, delete
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, \
    KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User, async_session, Recipe, Recipe_ingredient, Ingredient, Category, Cuisine, Type, IngredientType
from app.database.requests import set_user, get_ingredients_by_type
from app.yookassa_payment import create_payment
import app.keyboards as kb

router = Router()

class Form(StatesGroup):
    waiting_for_first_menu = State()
    at_first_menu = State()
    waiting_for_diet = State()
    waiting_for_category = State()
    waiting_for_country = State()
    waiting_for_ingridientCategory = State()
    waiting_for_ingridients = State()
    waiting_for_name = State()
    waiting_for_login = State()
    waiting_for_recipe_search = State()

# Определяем список состояний в порядке их использования
form_states = [
    Form.waiting_for_first_menu,
    Form.waiting_for_diet,
    Form.waiting_for_category,
    Form.waiting_for_country,
    Form.waiting_for_ingridientCategory,
    Form.waiting_for_ingridients,
    Form.waiting_for_name,
    Form.waiting_for_login,
    Form.waiting_for_recipe_search,
]

class AdminStates(StatesGroup):
    waiting_for_recipe_title = State()
    waiting_for_recipe_instructions = State()
    waiting_for_recipe_category = State()
    waiting_for_recipe_type = State()
    waiting_for_recipe_cuisine = State()
    waiting_for_recipe_ingredients = State()
    waiting_for_ingredient_selection = State()
    waiting_for_diet_name = State()
    waiting_for_category_name = State()
    waiting_for_cuisine_name = State()
    waiting_for_ingredient_name = State()
    waiting_for_ingredient_category = State()
    waiting_for_ingredient_protein = State()
    waiting_for_ingredient_fat = State()
    waiting_for_ingredient_carbohydrate = State()
    waiting_for_recipe_to_edit = State()
    waiting_for_recipe_to_delete = State()

def clean_text(text: str) -> str:
    if text is None:
        return ""
    return re.sub(r'[^\w\s]', '', text).strip()

def clean_button_texts(button_texts: List[str]) -> List[str]:
    return [clean_text(text) for text in button_texts]

async def get_user(session: AsyncSession, tg_id: int) -> Optional[User]:
    return await session.scalar(select(User).where(User.tg_id == tg_id))

async def create_user(session: AsyncSession, tg_id: int, login: str, name: str, is_trial: bool = True) -> User:
    user = User(
        tg_id=tg_id,
        login=login,
        name=name,
        is_trial=is_trial,
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=3 if is_trial else 365)
    )
    session.add(user)
    await session.commit()
    return user

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, user_id: int = None):
    target_user_id = user_id if user_id is not None else message.from_user.id
    async with async_session() as session:
        user = await get_user(session, target_user_id)
        if user:
            welcome_message = f"Добро пожаловать, {user.name}!"
            if user.end_date and user.end_date > datetime.now():
                await message.answer(welcome_message, reply_markup=kb.authorized_main)
            else:
                await message.answer(f"{welcome_message}\nВаша подписка истекла.", reply_markup=kb.expired_subscription_main)
        else:
            await message.answer("Добро пожаловать! Выберите действие:", reply_markup=kb.unauthorized_main)
    await state.set_state(Form.waiting_for_first_menu)

@router.message(F.text == "Назад")
async def back_button(message: Message, state: FSMContext):
    await message.answer("Возврат")
    await state.set_state(Form.waiting_for_first_menu)
    await cmd_start(message, state, user_id=message.from_user.id)

@router.message(F.text == "/testback")
async def handle_back(message: Message, state: FSMContext):
    current_state = await state.get_state()
    try:
        current_index = form_states.index(current_state)
        if current_index > 0:
            previous_state = form_states[current_index - 1]
            await state.set_state(previous_state)
            if previous_state == Form.waiting_for_diet:
                await show_diet_options(message, state)
            elif previous_state == Form.waiting_for_category:
                await show_category_options(message, state)
            elif previous_state == Form.waiting_for_country:
                await show_country_options(message, state)
            elif previous_state == Form.waiting_for_ingridientCategory:
                await show_ingridientCategory_options(message, state)
        else:
            await message.answer("Вы уже в начале.")
    except ValueError:
        await message.answer("Невозможно вернуться назад.")

@router.message(lambda message: clean_text(message.text) == 'Помощь', Form.waiting_for_first_menu)
async def handle_help(message: Message, state: FSMContext):
    await state.set_state(Form.at_first_menu)
    await message.answer('Страница помощи', reply_markup=kb.back)

@router.message(lambda message: clean_text(message.text) == 'Попробовать бесплатно 3 дня', Form.waiting_for_first_menu)
async def handle_trial(message: Message, state: FSMContext):
    async with async_session() as session:
        user = await get_user(session, message.from_user.id)
        if user and user.is_trial and user.end_date > datetime.now():
            await message.answer(f"Вы уже активировали пробный период. Он закончится через {(user.end_date - datetime.now()).days} дней.")
            return
        await state.set_state(Form.waiting_for_name)
        await message.answer("Как к вам обращаться?")

@router.message(Form.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Form.waiting_for_login)
    await message.answer("Придумайте уникальное имя аккаунта:")

@router.message(Form.waiting_for_login)
async def process_login(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data.get('name')
    login = message.text

    if len(login) < 3 or len(login) > 20:
        await message.answer("Логин должен быть от 3 до 20 символов.")
        return
    if not re.match(r"^[a-zA-Z0-9_]+$", login):
        await message.answer("Логин может содержать только буквы на англ, цифры и символ '_'.")
        return

    async with async_session() as session:
        existing_login = await session.scalar(select(User).where(User.login == login, User.tg_id != message.from_user.id))
        if existing_login:
            await message.answer("Это имя аккаунта уже занято. Пожалуйста, выберите другое.")
            return

        existing_user = await get_user(session, message.from_user.id)
        if existing_user:
            if not existing_user.is_trial or existing_user.end_date <= datetime.now():
                existing_user.login = login
                existing_user.name = name
                existing_user.is_trial = True
                existing_user.start_date = datetime.now()
                existing_user.end_date = datetime.now() + timedelta(days=3)
                await session.commit()
                await message.answer("Регистрация завершена! Теперь у вас есть доступ к пробному периоду на 3 дня.", reply_markup=kb.back)
            else:
                await message.answer(f"Вы уже активировали пробный период. Он закончится через {(existing_user.end_date - datetime.now()).days} дней.")
                return
        else:
            await create_user(session, message.from_user.id, login, name)
            await message.answer("Регистрация завершена! Теперь у вас есть доступ к пробному периоду на 3 дня.", reply_markup=kb.back)

    await state.set_state(Form.at_first_menu)

async def notify_trial_end(bot: Bot, user_id: int):
    await bot.send_message(user_id, "Ваш пробный период закончился. Пожалуйста, перейдите на полную версию.")

@router.message(lambda message: clean_text(message.text) == 'Получить доступ к полной версии')
async def handle_full_access(message: Message, state: FSMContext):
    payment = await create_payment(amount=1, description="Оплата полной версии", metadata={"user_id": message.from_user.id})
    if payment.get("status") == "pending":
        await message.answer(f"Оплатите по ссылке: {payment['confirmation']['confirmation_url']}")
    else:
        await message.answer("Произошла ошибка при создании платежа. Пожалуйста, попробуйте позже.")

async def update_user_access(user_id: int):
    async with async_session() as session:
        user = await get_user(session, user_id)
        if user:
            user.is_trial = False
            user.end_date = datetime.now() + timedelta(days=365)
            await session.commit()
            return True
        return False

@router.message(lambda message: clean_text(message.text) == 'Перейти к рецептам')
async def handle_recipes(message: Message, state: FSMContext):
    async with async_session() as session:
        user = await get_user(session, message.from_user.id)
        if user:
            if user.end_date and user.end_date > datetime.now():
                await state.set_state(Form.waiting_for_diet)
                await message.answer("Smart Cookbook рекомендует вам внимательно ознакомится со списком ингредиентов блюд и не использовать в приготовлении ингредиенты содержащие известные вам аллергены. Smart Cookbook рекомендует придерживаться сбалансированного рациона если не имеется медицинских противопоказаний.", reply_markup=kb.diet)
            else:
                await message.answer("Ваша подписка истекла. Пожалуйста, оплатите полную версию, чтобы продолжить.", reply_markup=kb.expired_subscription_main)
        else:
            await message.answer("Для доступа к рецептам необходимо зарегистрироваться.", reply_markup=kb.unauthorized_main)

@router.message(Form.waiting_for_diet)
async def show_diet_options(message: Message, state: FSMContext):
    valid_options = clean_button_texts(get_button_texts(kb.diet))
    if clean_text(message.text.lower()) == "не важно":
        await state.update_data(selected_diet=None)
        await state.set_state(Form.waiting_for_category)
        await message.answer("Пожалуйста, выберите один из предложенных вариантов.", reply_markup=kb.category)
        return
    if clean_text(message.text) not in valid_options:
        await message.answer("Пожалуйста, выберите один из предложенных вариантов.", reply_markup=kb.diet)
        return
    await state.update_data(selected_diet=clean_text(message.text))
    await state.set_state(Form.waiting_for_category)
    await message.answer("Пожалуйста, выберите один из предложенных вариантов.", reply_markup=kb.category)

@router.message(Form.waiting_for_category)
async def show_category_options(message: Message, state: FSMContext):
    valid_options = clean_button_texts(get_button_texts(kb.category))
    if clean_text(message.text.lower()) == "не важно":
        await state.update_data(selected_categorys=None)
        await state.set_state(Form.waiting_for_country)
        await message.answer("Пожалуйста, выберите один из предложенных вариантов.", reply_markup=kb.country)
        return
    if clean_text(message.text) not in valid_options:
        await message.answer("Пожалуйста, выберите один из предложенных вариантов.", reply_markup=kb.category)
        return
    await state.update_data(selected_categorys=clean_text(message.text))
    await state.set_state(Form.waiting_for_country)
    await show_country_options(message, state)

@router.message(Form.waiting_for_country)
async def show_country_options(message: Message, state: FSMContext):
    valid_options = clean_button_texts(get_button_texts(kb.country))
    if clean_text(message.text.lower()) == "не важно":
        await state.update_data(selected_country=None)
        await state.set_state(Form.waiting_for_ingridientCategory)
        await show_ingridientCategory_options(message, state)
        return
    if clean_text(message.text) not in valid_options:
        await message.answer("Пожалуйста, выберите один из предложенных вариантов.", reply_markup=kb.country)
        return
    await state.update_data(selected_country=clean_text(message.text))
    await state.set_state(Form.waiting_for_ingridientCategory)
    await show_ingridientCategory_options(message, state)

@router.message(Form.waiting_for_ingridientCategory)
async def show_ingridientCategory_options(message: Message, state: FSMContext):
    valid_options = clean_button_texts(get_button_texts(kb.ingridientCategory))
    if clean_text(message.text) not in valid_options:
        await message.answer("Пожалуйста, выберите один из предложенных вариантов.", reply_markup=kb.ingridientCategory)
        return
    if clean_text(message.text) == "Показать рецепты":
        await state.set_state(Form.waiting_for_recipe_search)
        await handle_go_to_recipes(message, state)
        return
    await state.update_data(selected_ingridientCategory=clean_text(message.text))
    await state.set_state(Form.waiting_for_ingridients)
    await show_ingridients_checkboxes(message, state)

@router.message(Form.waiting_for_ingridients)
async def show_ingridients_checkboxes(message: Message, state: FSMContext):
    # Получаем данные из состояния
    data = await state.get_data()

    # Если пользователь нажал "Готово", игнорируем это сообщение
    if message.text == "Готово":
        await state.set_state(Form.waiting_for_ingridientCategory)
        await message.answer('Возврат')
        await show_ingridientCategory_options(message, state)
        return  # Пропускаем обработку, так как "Готово" уже обработано в другом обработчике

    # Очищаем текст от смайликов и лишних символов
    cleaned_text = re.sub(r'[^\w\s]', '', message.text).strip()
    print(cleaned_text)

    # Получаем текущие данные состояния
    selected_category = data.get('selected_category')
    print("11  ", selected_category)

    # Если категория не сохранена в состоянии, используем очищенный текст
    selected_category = cleaned_text

    # Сохраняем выбранную категорию в состоянии
    await state.update_data(selected_category=selected_category, current_page=0)  # Начинаем с первой страницы

    # Логирование для отладки
    print(f"Выбранная категория: {selected_category}")

    async with async_session() as session:
        try:
            # Создаем чекбоксы для выбранной категории
            checkboxes = await create_ingridients_checkboxes(selected_category, data.get('selected_ingridients', []), session, 0)

            # Отправляем сообщение с чекбоксами
            await message.answer('Выберите ингредиенты:', reply_markup=checkboxes)

            # Отправляем сообщение с кнопкой "Готово"
            await message.answer('Когда закончите, нажмите "Готово":', reply_markup=create_done_keyboard())
        except ValueError as e:
            await message.answer(str(e))

@router.message(Form.waiting_for_ingridients, lambda message: clean_text(message.text) == "Готово")
async def handle_done(message: Message, state: FSMContext):
    data = await state.get_data()
    selected_ingridients = data.get('selected_ingridients', [])
    await state.update_data(selected_ingridients=selected_ingridients)
    await state.set_state(Form.waiting_for_ingridientCategory)
    await message.answer('Выберите следующий шаг:', reply_markup=kb.ingridientCategory)

@router.callback_query(F.data.startswith("ingridient_"))
async def handle_ingridient_selection(callback: CallbackQuery, state: FSMContext):
    ingridient = callback.data.split("_")[1]
    data = await state.get_data()
    selected_ingridients = data.get('selected_ingridients', [])
    current_page = data.get('current_page', 0)
    selected_category = data.get('selected_category')
    if not selected_category:
        await callback.answer("Ошибка: категория не выбрана.")
        return
    if ingridient in selected_ingridients:
        selected_ingridients.remove(ingridient)
    else:
        selected_ingridients.append(ingridient)
    await state.update_data(selected_ingridients=selected_ingridients)
    async with async_session() as session:
        try:
            await update_ingridients_checkboxes(callback.message, selected_category, selected_ingridients, session, current_page)
        except ValueError as e:
            await callback.answer(str(e))

async def update_ingridients_checkboxes(message: Message, selected_category: str, selected_ingridients: list, session: AsyncSession, current_page: int):
    if not selected_category:
        await message.answer("Ошибка: категория не выбрана.")
        return
    try:
        checkboxes = await create_ingridients_checkboxes(selected_category, selected_ingridients, session, current_page)
        await message.edit_text('Выберите ингредиенты:', reply_markup=checkboxes)
    except ValueError as e:
        await message.answer(str(e))

@router.message(F.text == "Показать рецепты", Form.waiting_for_recipe_search)
async def handle_go_to_recipes(message: Message, state: FSMContext):
    data = await state.get_data()
    selected_ingridients = data.get('selected_ingridients', [])
    selected_diet = data.get('selected_diet')
    selected_categorys = data.get('selected_categorys')
    selected_country = data.get('selected_country')
    await state.set_state(Form.waiting_for_recipe_search)
    await search_recipes(message, state)

async def search_recipes(message: Message, state: FSMContext):
    data = await state.get_data()
    selected_diet = data.get('selected_diet')
    selected_categorys = data.get('selected_categorys')
    selected_country = data.get('selected_country')
    selected_ingridients = data.get('selected_ingridients', [])
    async with async_session() as session:
        user = await get_user(session, message.from_user.id)
        is_trial = user.is_trial if user else True
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
        if is_trial:
            recipes = recipes[:3]
        else:
            recipes = recipes[:10]
        if not recipes:
            await reset_search_parameters(state)
            await message.answer("Рецепты по вашему запросу не найдены.")
            await state.set_state(Form.waiting_for_first_menu)
            await cmd_start(message, state, user_id=message.from_user.id)
            return
        await state.update_data(recipes=recipes, current_recipe_index=0)
        await send_recipe(message, state)

async def send_recipe(message: Message, state: FSMContext):
    data = await state.get_data()
    recipes = data.get('recipes', [])
    current_recipe_index = data.get('current_recipe_index', 0)
    if not recipes or current_recipe_index >= len(recipes):
        await message.answer("Рецепты не найдены.")
        await state.set_state(Form.waiting_for_first_menu)
        await cmd_start(message, state, user_id=message.from_user.id)
        return
    recipe = recipes[current_recipe_index]
    async with async_session() as session:
        ingredients_query = select(Ingredient.name).join(
            Recipe_ingredient, Ingredient.id == Recipe_ingredient.ingredient_id
        ).where(Recipe_ingredient.recipe_id == recipe.id)
        ingredients_result = await session.execute(ingredients_query)
        ingredients = [ing[0] for ing in ingredients_result]
        recipe_text = (
            f"🍴 <b>{recipe.title}</b>\n\n"
            f"<b>Ингредиенты:</b>\n"
            f"{', '.join(ingredients)}\n\n"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="prev_recipe")],
            [InlineKeyboardButton(text="Готовим 🍳", callback_data="cook_recipe")],
            [InlineKeyboardButton(text="➡️ Следующий", callback_data="next_recipe")]
        ])
        if "recipe_message_id" not in data:
            sent_message = await message.answer(recipe_text, reply_markup=keyboard, parse_mode="HTML")
            await state.update_data(recipe_message_id=sent_message.message_id)
        else:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=data["recipe_message_id"],
                    text=recipe_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            except TelegramBadRequest:
                sent_message = await message.answer(recipe_text, reply_markup=keyboard, parse_mode="HTML")
                await state.update_data(recipe_message_id=sent_message.message_id)

@router.callback_query(F.data == "prev_recipe")
async def handle_prev_recipe(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_recipe_index = data.get('current_recipe_index', 0)
    if current_recipe_index > 0:
        await state.update_data(current_recipe_index=current_recipe_index - 1)
        await send_recipe(callback.message, state)
    else:
        await callback.answer("Это первый рецепт.")

@router.callback_query(F.data == "next_recipe")
async def handle_next_recipe(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_recipe_index = data.get('current_recipe_index', 0)
    recipes = data.get('recipes', [])
    if current_recipe_index < len(recipes) - 1:
        await state.update_data(current_recipe_index=current_recipe_index + 1)
        await send_recipe(callback.message, state)
    else:
        await callback.answer("Это последний рецепт.")

@router.callback_query(F.data == "cook_recipe")
async def handle_cook_recipe(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    recipes = data.get('recipes', [])
    current_recipe_index = data.get('current_recipe_index', 0)
    if recipes and current_recipe_index < len(recipes):
        recipe = recipes[current_recipe_index]
        async with async_session() as session:
            ingredients_query = select(Ingredient.name).join(
                Recipe_ingredient, Ingredient.id == Recipe_ingredient.ingredient_id
            ).where(Recipe_ingredient.recipe_id == recipe.id)
            ingredients_result = await session.execute(ingredients_query)
            ingredients = [ing[0] for ing in ingredients_result]
            recipe_text = (
                f"🍴 <b>{recipe.title}</b>\n\n"
                f"<b>Ингредиенты:</b>\n"
                f"{', '.join(ingredients)}\n\n"
                f"<b>Инструкция:</b>\n"
                f"{recipe.instructions}"
            )
            await callback.message.answer(recipe_text, parse_mode="HTML")
            await callback.message.answer("Мы едим, чтобы жить и получать удовольствие. То, как мы питаемся, влияет на продолжительность и качество жизни. Вылечиться от болезней едой мы не можем, но поддержать здоровье — запросто.")
            await callback.answer("Рецепт переслан. Работа бота завершена.")
            await reset_search_parameters(state)
            await state.set_state(Form.waiting_for_first_menu)
            await cmd_start(callback.message, state, user_id=callback.from_user.id)

async def reset_search_parameters(state: FSMContext):
    await state.update_data(
        selected_diet=None,
        selected_categorys=None,
        selected_country=None,
        selected_ingridients=[],
        selected_ingridientCategory=None,
        recipes=[],
        current_recipe_index=0,
        recipe_message_id=None,
    )

def get_button_texts(keyboard: ReplyKeyboardMarkup) -> List[str]:
    button_texts = []
    for row in keyboard.keyboard:
        for button in row:
            button_texts.append(button.text)
    return button_texts

@router.message(F.text == 'Ы')
async def gg(message: Message):
    await message.answer('OK!')

@router.callback_query(F.data.startswith("page_"), Form.waiting_for_ingridients)
async def handle_page_change(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[1])
    await state.update_data(current_page=page)
    data = await state.get_data()
    selected_category = data.get('selected_category')
    selected_ingridients = data.get('selected_ingridients', [])
    async with async_session() as session:
        try:
            checkboxes = await create_ingridients_checkboxes(selected_category, selected_ingridients, session, page)
            await callback.message.edit_text('Выберите ингредиенты:', reply_markup=checkboxes)
        except ValueError as e:
            await callback.answer(str(e))

async def create_ingridients_checkboxes(selected_category: str, selected_ingridients: list, session: AsyncSession, page: int) -> InlineKeyboardMarkup:
    try:
        ingredients = await get_ingredients_by_type(selected_category, session)
        total_pages = (len(ingredients) + 4) // 5
        start_index = page * 5
        end_index = start_index + 5
        page_ingredients = ingredients[start_index:end_index]
        checkboxes = [
            [InlineKeyboardButton(
                text=f"{'✅' if ingredient in selected_ingridients else '☑️'} {ingredient}",
                callback_data=f"ingridient_{ingredient}"
            )]
            for ingredient in page_ingredients
        ]
        navigation_buttons = []
        if page > 0:
            navigation_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page - 1}"))
        if page < total_pages - 1:
            navigation_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page_{page + 1}"))
        if navigation_buttons:
            checkboxes.append(navigation_buttons)
        return InlineKeyboardMarkup(inline_keyboard=checkboxes)
    except ValueError as e:
        raise e

def create_done_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Готово")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

ADMIN_IDS = [1292713978, 215081532, 6355347961]

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=kb.admin_panel)

@router.message(F.text == 'Добавить')
async def add_menu(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    await message.answer("Выберите, что хотите добавить:", reply_markup=kb.add_options)

@router.message(F.text == 'Изменить')
async def edit_menu(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    await message.answer("Выберите, что хотите изменить:", reply_markup=kb.edit_options)

@router.message(F.text == 'Изменить рецепт')
async def edit_recipe_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    await state.set_state(AdminStates.waiting_for_recipe_to_edit)
    await message.answer("Введите ID рецепта, который хотите изменить:")

@router.message(AdminStates.waiting_for_recipe_to_edit)
async def process_recipe_to_edit(message: Message, state: FSMContext):
    recipe_id = message.text
    async with async_session() as session:
        recipe = await session.scalar(select(Recipe).where(Recipe.id == int(recipe_id)))
        if not recipe:
            await message.answer(f"Рецепт с ID {recipe_id} не найден.")
            await state.clear()
            return
        await state.update_data(recipe_id=recipe_id)
        await state.set_state(AdminStates.waiting_for_recipe_title)
        await message.answer("Введите новое название рецепта:")

@router.message(F.text == 'Удалить рецепт')
async def delete_recipe_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    await state.set_state(AdminStates.waiting_for_recipe_to_delete)
    await message.answer("Введите ID рецепта, который хотите удалить:")

@router.message(AdminStates.waiting_for_recipe_to_delete)
async def process_recipe_to_delete(message: Message, state: FSMContext):
    recipe_id = message.text
    async with async_session() as session:
        recipe = await session.scalar(select(Recipe).where(Recipe.id == recipe_id))
        if recipe:
            await session.delete(recipe)
            await session.commit()
            await message.answer(f"Рецепт с ID {recipe_id} успешно удален.")
        else:
            await message.answer(f"Рецепт с ID {recipe_id} не найден.")
    await state.clear()
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=kb.admin_panel)

@router.message(F.text == 'Удалить')
async def delete_menu(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    await message.answer("Выберите, что хотите удалить:", reply_markup=kb.delete_options)

@router.message(F.text == 'Добавить рецепт')
async def add_recipe_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    await state.set_state(AdminStates.waiting_for_recipe_title)
    await message.answer("Введите название рецепта:")

@router.message(AdminStates.waiting_for_recipe_title)
async def process_recipe_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AdminStates.waiting_for_recipe_instructions)
    await message.answer("Введите новую инструкцию для рецепта:")

@router.message(AdminStates.waiting_for_recipe_instructions)
async def process_recipe_instructions(message: Message, state: FSMContext):
    await state.update_data(instructions=message.text)
    await state.set_state(AdminStates.waiting_for_recipe_category)
    await message.answer("Выберите новую категорию:", reply_markup=kb.category_keyboard)

@router.message(AdminStates.waiting_for_recipe_category)
async def process_recipe_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text)
    await state.set_state(AdminStates.waiting_for_recipe_type)
    await message.answer("Выберите новый тип диеты:", reply_markup=kb.diet_keyboard)

@router.message(AdminStates.waiting_for_recipe_type)
async def process_recipe_type(message: Message, state: FSMContext):
    await state.update_data(type=message.text)
    await state.set_state(AdminStates.waiting_for_recipe_cuisine)
    await message.answer("Выберите новую кухню:", reply_markup=kb.cuisine_keyboard)

@router.message(AdminStates.waiting_for_recipe_cuisine)
async def process_recipe_cuisine(message: Message, state: FSMContext):
    await state.update_data(cuisine=message.text)
    await state.set_state(AdminStates.waiting_for_recipe_ingredients)
    await start_ingredient_selection(message, state)

async def update_recipe_in_db(message: Message, state: FSMContext):
    data = await state.get_data()
    recipe_id = data.get("recipe_id")
    selected_ingredients = data.get("ingredients", [])
    async with async_session() as session:
        recipe = await session.scalar(select(Recipe).where(Recipe.id == int(recipe_id)))
        if not recipe:
            await message.answer(f"Рецепт с ID {recipe_id} не найден.")
            return
        category = await session.scalar(select(Category).where(Category.name == data['category']))
        type_ = await session.scalar(select(Type).where(Type.name == data['type']))
        cuisine = await session.scalar(select(Cuisine).where(Cuisine.name == data['cuisine']))
        if not category:
            await message.answer(f"Категория '{data['category']}' не найдена. Пожалуйста, используйте существующую категорию.")
            return
        if not type_:
            await message.answer(f"Тип диеты '{data['type']}' не найден. Пожалуйста, используйте существующий тип.")
            return
        if not cuisine:
            await message.answer(f"Кухня '{data['cuisine']}' не найдена. Пожалуйста, используйте существующую кухню.")
            return
        recipe.title = data['title']
        recipe.instructions = data['instructions']
        recipe.category_id = category.id
        recipe.type_id = type_.id
        recipe.cuisine_id = cuisine.id
        await session.execute(delete(Recipe_ingredient).where(Recipe_ingredient.recipe_id == recipe.id))
        for ingredient_name in selected_ingredients:
            ingredient = await get_or_create_ingredient(session, ingredient_name)
            recipe_ingredient = Recipe_ingredient(recipe_id=recipe.id, ingredient_id=ingredient.id)
            session.add(recipe_ingredient)
        await session.commit()
    await message.answer("Рецепт успешно обновлен!")
    await state.clear()
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=kb.admin_panel)

async def create_ingredients_checkboxes(session: AsyncSession, selected_ingredients: list = None, page: int = 0, per_page: int = 20) -> InlineKeyboardMarkup:
    if selected_ingredients is None:
        selected_ingredients = []
    ingredients = await session.execute(select(Ingredient))
    ingredients = ingredients.scalars().all()
    total_pages = (len(ingredients) // per_page + (1 if len(ingredients) % per_page > 0 else 0))
    start_index = page * per_page
    end_index = start_index + per_page
    page_ingredients = ingredients[start_index:end_index]
    checkboxes = [
        [InlineKeyboardButton(
            text=f"{'✅' if ingredient.name in selected_ingredients else '☑️'} {ingredient.name}",
            callback_data=f"ingredient_{ingredient.name}"
        )]
        for ingredient in page_ingredients
    ]
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page - 1}"))
    if page < total_pages - 1:
        navigation_buttons.append(InlineKeyboardButton(text="➡️ Вперед", callback_data=f"page_{page + 1}"))
    if navigation_buttons:
        checkboxes.append(navigation_buttons)
    checkboxes.append([InlineKeyboardButton(text="Готово", callback_data="done_ingredients")])
    return InlineKeyboardMarkup(inline_keyboard=checkboxes)

@router.message(AdminStates.waiting_for_recipe_ingredients)
async def start_ingredient_selection(message: Message, state: FSMContext):
    await state.update_data(selected_ingredients=[], current_page=0)
    async with async_session() as session:
        checkboxes = await create_ingredients_checkboxes(session, page=0)
        await message.answer("Выберите ингредиенты:", reply_markup=checkboxes)
        await state.set_state(AdminStates.waiting_for_ingredient_selection)

@router.callback_query(F.data.startswith("page_"), AdminStates.waiting_for_ingredient_selection)
async def handle_page_change(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[1])
    await state.update_data(current_page=page)
    data = await state.get_data()
    selected_ingredients = data.get("selected_ingredients", [])
    async with async_session() as session:
        checkboxes = await create_ingredients_checkboxes(session, selected_ingredients, page)
        await callback.message.edit_reply_markup(reply_markup=checkboxes)
    await callback.answer()

async def add_recipe_to_db(message: Message, state: FSMContext):
    data = await state.get_data()
    selected_ingredients = data.get("ingredients", [])
    async with async_session() as session:
        category = await session.scalar(select(Category).where(Category.name == data['category']))
        type_ = await session.scalar(select(Type).where(Type.name == data['type']))
        cuisine = await session.scalar(select(Cuisine).where(Cuisine.name == data['cuisine']))
        if not category:
            await message.answer(f"Категория '{data['category']}' не найдена. Пожалуйста, используйте существующую категорию.")
            return
        if not type_:
            await message.answer(f"Тип диеты '{data['type']}' не найден. Пожалуйста, используйте существующий тип.")
            return
        if not cuisine:
            await message.answer(f"Кухня '{data['cuisine']}' не найдена. Пожалуйста, используйте существующую кухню.")
            return
        recipe = Recipe(
            title=data['title'],
            instructions=data['instructions'],
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
    await message.answer("Рецепт успешно добавлен!")
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=kb.admin_panel)

@router.callback_query(F.data.startswith("ingredient_"), AdminStates.waiting_for_ingredient_selection)
async def handle_ingredient_selection(callback: CallbackQuery, state: FSMContext):
    ingredient_name = callback.data.split("_")[1]
    data = await state.get_data()
    selected_ingredients = data.get("selected_ingredients", [])
    current_page = data.get("current_page", 0)
    if ingredient_name in selected_ingredients:
        selected_ingredients.remove(ingredient_name)
    else:
        selected_ingredients.append(ingredient_name)
    await state.update_data(selected_ingredients=selected_ingredients)
    async with async_session() as session:
        checkboxes = await create_ingredients_checkboxes(session, selected_ingredients, current_page)
        await callback.message.edit_reply_markup(reply_markup=checkboxes)
    await callback.answer()

@router.callback_query(F.data == "done_ingredients", AdminStates.waiting_for_ingredient_selection)
async def handle_done_ingredients(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_ingredients = data.get("selected_ingredients", [])
    if not selected_ingredients:
        await callback.answer("Вы не выбрали ни одного ингредиента.")
        return
    await state.update_data(ingredients=selected_ingredients)
    if "recipe_id" in data:
        await update_recipe_in_db(callback.message, state)
    else:
        await add_recipe_to_db(callback.message, state)

@router.message(AdminStates.waiting_for_recipe_ingredients)
async def process_recipe_ingredients(message: Message, state: FSMContext):
    data = await state.get_data()
    selected_ingredients = data.get("ingredients", [])
    async with async_session() as session:
        category = await session.scalar(select(Category).where(Category.name == data['category']))
        type_ = await session.scalar(select(Type).where(Type.name == data['type']))
        cuisine = await session.scalar(select(Cuisine).where(Cuisine.name == data['cuisine']))
        if not category:
            await message.answer(f"Категория '{data['category']}' не найдена. Пожалуйста, используйте существующую категорию.")
            return
        if not type_:
            await message.answer(f"Тип диеты '{data['type']}' не найден. Пожалуйста, используйте существующий тип.")
            return
        if not cuisine:
            await message.answer(f"Кухня '{data['cuisine']}' не найдена. Пожалуйста, используйте существующую кухню.")
            return
        recipe = Recipe(
            title=data['title'],
            instructions=data['instructions'],
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
    await message.answer("Рецепт успешно добавлен!")
    await state.clear()
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=kb.admin_panel)

@router.message(F.text == 'Добавить ингредиент')
async def add_ingredient_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    await state.set_state(AdminStates.waiting_for_ingredient_name)
    await message.answer("Введите название ингредиента:")

@router.message(AdminStates.waiting_for_ingredient_name)
async def process_ingredient_name(message: Message, state: FSMContext):
    await state.update_data(ingredient_name=message.text)
    await state.set_state(AdminStates.waiting_for_ingredient_category)
    await message.answer("Выберите категорию ингредиента:", reply_markup=kb.ingridientCategory)

@router.message(AdminStates.waiting_for_ingredient_category)
async def process_ingredient_category(message: Message, state: FSMContext):
    category_name = clean_text(message.text)
    await state.update_data(ingredient_category=category_name)
    await state.set_state(AdminStates.waiting_for_ingredient_protein)
    await message.answer("Введите количество белков (в граммах на 100 г продукта):")

@router.message(AdminStates.waiting_for_ingredient_protein)
async def process_ingredient_protein(message: Message, state: FSMContext):
    protein = message.text
    try:
        protein = float(protein)
    except ValueError:
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(ingredient_protein=protein)
    await state.set_state(AdminStates.waiting_for_ingredient_fat)
    await message.answer("Введите количество жиров (в граммах на 100 г продукта):")

@router.message(AdminStates.waiting_for_ingredient_fat)
async def process_ingredient_fat(message: Message, state: FSMContext):
    fat = message.text
    try:
        fat = float(fat)
    except ValueError:
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(ingredient_fat=fat)
    await state.set_state(AdminStates.waiting_for_ingredient_carbohydrate)
    await message.answer("Введите количество углеводов (в граммах на 100 г продукта):")

@router.message(AdminStates.waiting_for_ingredient_carbohydrate)
async def process_ingredient_carbohydrate(message: Message, state: FSMContext):
    carbohydrate = message.text
    try:
        carbohydrate = float(carbohydrate)
    except ValueError:
        await message.answer("Пожалуйста, введите число.")
        return
    data = await state.get_data()
    ingredient_name = data.get("ingredient_name")
    category_name = data.get("ingredient_category")
    protein = data.get("ingredient_protein")
    fat = data.get("ingredient_fat")
    async with async_session() as session:
        existing_ingredient = await session.scalar(select(Ingredient).where(Ingredient.name == ingredient_name))
        if existing_ingredient:
            await message.answer(f"Ингредиент '{ingredient_name}' уже существует.")
            return
        category = await session.scalar(select(IngredientType).where(IngredientType.name == category_name))
        if not category:
            await message.answer(f"Категория '{category_name}' не найдена.")
            return
        ingredient = Ingredient(
            name=ingredient_name,
            protein=protein,
            fat=fat,
            carbohydrate=carbohydrate,
            ingredient_type_id=category.id
        )
        session.add(ingredient)
        await session.commit()
        await session.refresh(ingredient)
    await message.answer(f"Ингредиент '{ingredient_name}' успешно добавлен в категорию '{category_name}'!")
    await state.clear()
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=kb.admin_panel)

@router.message(F.text == 'Добавить кухню')
async def add_cuisine_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    await state.set_state(AdminStates.waiting_for_cuisine_name)
    await message.answer("Введите название кухни:")

@router.message(AdminStates.waiting_for_cuisine_name)
async def process_cuisine_name(message: Message, state: FSMContext):
    cuisine_name = message.text
    async with async_session() as session:
        existing_cuisine = await session.scalar(select(Cuisine).where(Cuisine.name == cuisine_name))
        if existing_cuisine:
            await message.answer(f"Кухня '{cuisine_name}' уже существует.")
            return
        cuisine = Cuisine(name=cuisine_name)
        session.add(cuisine)
        await session.commit()
        await session.refresh(cuisine)
    await message.answer(f"Кухня '{cuisine_name}' успешно добавлена!")
    await state.clear()
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=kb.admin_panel)

@router.message(F.text == 'Добавить диету')
async def add_diet_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    await state.set_state(AdminStates.waiting_for_diet_name)
    await message.answer("Введите название диеты:")

@router.message(AdminStates.waiting_for_diet_name)
async def process_diet_name(message: Message, state: FSMContext):
    diet_name = message.text
    async with async_session() as session:
        existing_diet = await session.scalar(select(Type).where(Type.name == diet_name))
        if existing_diet:
            await message.answer(f"Диета '{diet_name}' уже существует.")
            return
        diet = Type(name=diet_name)
        session.add(diet)
        await session.commit()
    await message.answer(f"Диета '{diet_name}' успешно добавлена!")
    await state.clear()
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=kb.admin_panel)

@router.message(F.text == 'Добавить категорию')
async def add_category_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    await state.set_state(AdminStates.waiting_for_category_name)
    await message.answer("Введите название категории:")

@router.message(AdminStates.waiting_for_category_name)
async def process_category_name(message: Message, state: FSMContext):
    category_name = message.text
    async with async_session() as session:
        existing_category = await session.scalar(select(Category).where(Category.name == category_name))
        if existing_category:
            await message.answer(f"Категория '{category_name}' уже существует.")
            return
        category = Category(name=category_name)
        session.add(category)
        await session.commit()
    await message.answer(f"Категория '{category_name}' успешно добавлена!")
    await state.clear()
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=kb.admin_panel)

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

async def get_or_create_ingredient(session: AsyncSession, name: str) -> Ingredient:
    ingredient = await session.scalar(select(Ingredient).where(Ingredient.name == name))
    if not ingredient:
        ingredient = Ingredient(name=name)
        session.add(ingredient)
        await session.commit()
    return ingredient