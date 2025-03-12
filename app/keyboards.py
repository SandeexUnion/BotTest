from aiogram.types import  ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardButton, InlineKeyboardBuilder
from aiogram_dialog import DialogManager, ChatEvent
from aiogram_dialog.widgets.kbd import Checkbox, ManagedCheckbox
from aiogram_dialog.widgets.text import Const


back = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Назад')]

],resize_keyboard=True)

# Клавиатура для неавторизованных пользователей
unauthorized_main = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='🛟Помощь')],
    [KeyboardButton(text='⚖️Попробовать бесплатно 3 дня')],
    [KeyboardButton(text='🗝Получить доступ к полной версии')],
], resize_keyboard=True)

# Клавиатура для авторизованных пользователей
authorized_main = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='🛟Помощь')],
    [KeyboardButton(text='🗝Получить доступ к полной версии')],
    [KeyboardButton(text='Перейти к рецептам')],
], resize_keyboard=True)

# Клавиатура для авторизованных пользователей с истекшей подпиской
expired_subscription_main = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='🛟Помощь')],
    [KeyboardButton(text='🗝Получить доступ к полной версии')],
], resize_keyboard=True)

diet = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='✝️Постное')],
    [KeyboardButton(text='✡️Кошерное')],
    [KeyboardButton(text='☪️Халяль')],
    [KeyboardButton(text='🌎Не важно')]
])

category = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='🥣Первое блюдо')],
    [KeyboardButton(text='🍲Второе блюдо')],
    [KeyboardButton(text='🥗Салат')],
    [KeyboardButton(text='🍱Закуска')],
    [KeyboardButton(text='🍚Гарнир')],
    [KeyboardButton(text='🥘Не важно')]
])

country = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='🍳Русская кухня')],
    [KeyboardButton(text='🍕Европейская кухня')],
    [KeyboardButton(text='🍖Кавказская кухня')],
    [KeyboardButton(text='🥢Паназиатская кухня')],
    [KeyboardButton(text='🌭Американская кухня')],
    [KeyboardButton(text='🍛Центрально-азиатская кухня')],
    [KeyboardButton(text='🥫Африканская кухня')],
    [KeyboardButton(text='🍽Не важно')],

])

ingridientCategory = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='🥩Мясо')],
    [KeyboardButton(text='🐓Птица')],
    [KeyboardButton(text='🥓Мясопродукты')],
    [KeyboardButton(text='🐟Рыба')],
    [KeyboardButton(text='🦀Морепродукты')],
    [KeyboardButton(text='🫑Овощи')],
    [KeyboardButton(text='🫘Бакалея')],
    [KeyboardButton(text='🔍Показать рецепты')]

])


admin_panel = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Добавить')],
    [KeyboardButton(text='Изменить')],
    [KeyboardButton(text='Удалить')],
    [KeyboardButton(text='Назад')]
], resize_keyboard=True)

add_options = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Добавить рецепт')],
    [KeyboardButton(text='Добавить ингредиент')],
    [KeyboardButton(text='Добавить кухню')],
    [KeyboardButton(text='Добавить диету')],
    [KeyboardButton(text='Добавить категорию')],
    [KeyboardButton(text='Назад')]
], resize_keyboard=True)

edit_options = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Изменить рецепт')],
    [KeyboardButton(text='Изменить ингредиент')],
    [KeyboardButton(text='Изменить кухню')],
    [KeyboardButton(text='Изменить диету')],
    [KeyboardButton(text='Изменить категорию')],
    [KeyboardButton(text='Назад')]
], resize_keyboard=True)

delete_options = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Удалить рецепт')],
    [KeyboardButton(text='Удалить ингредиент')],
    [KeyboardButton(text='Удалить кухню')],
    [KeyboardButton(text='Удалить диету')],
    [KeyboardButton(text='Удалить категорию')],
    [KeyboardButton(text='Назад')]
], resize_keyboard=True)

# Клавиатура для выбора диеты
diet_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Постное")],
        [KeyboardButton(text="Кошерное")],
        [KeyboardButton(text="Халяль")],
        [KeyboardButton(text="Не важно")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# Клавиатура для выбора категории
category_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Первое блюдо")],
        [KeyboardButton(text="Второе блюдо")],
        [KeyboardButton(text="Салат")],
        [KeyboardButton(text="Закуска")],
        [KeyboardButton(text="Гарнир")],
        [KeyboardButton(text="Не важно")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# Клавиатура для выбора кухни
cuisine_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Русская кухня")],
        [KeyboardButton(text="Европейская кухня")],
        [KeyboardButton(text="Кавказская кухня")],
        [KeyboardButton(text="Паназиатская кухня")],
        [KeyboardButton(text="Американская кухня")],
        [KeyboardButton(text="Центрально-азиатская кухня")],
        [KeyboardButton(text="Африканская кухня")],
        [KeyboardButton(text="Не важно")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)


