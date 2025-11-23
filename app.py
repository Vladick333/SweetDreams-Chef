import streamlit as st
import joblib
import json
import os
import time
import numpy as np
import pandas as pd
import google.generativeai as genai
from datetime import datetime
import uuid
import random
import streamlit.components.v1 as components
# === БИБЛИОТЕКИ ДЛЯ ВХОДА И РЕГИСТРАЦИИ ===
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import bcrypt # <--- ДОБАВИТЬ ЭТО К ОСТАЛЬНЫМ ИМПОРТАМ
# ==========================================

# ==============================================================================
# 1. НАСТРОЙКИ СТРАНИЦЫ
# ==============================================================================
st.set_page_config(
    page_title="Vladыка AI [v24.0]",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# !!! 1.1. ЗАГРУЗКА КЛЮЧЕЙ (ДЛЯ БОТА) !!!
try:
    raw_keys = st.secrets["GEMINI_API_KEY"]
    if isinstance(raw_keys, str):
        API_KEYS_POOL = [raw_keys]
    else:
        API_KEYS_POOL = raw_keys
except KeyError:
    st.error("⚠️ Ошибка: Ключ GEMINI_API_KEY не найден в Secrets.")
    API_KEYS_POOL = []

# ==============================================================================
# 1.2. АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ (ИСПРАВЛЕНО: BCRYPT + ПЕРЕВОД)
# ==============================================================================
try:
    with open('config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)
except FileNotFoundError:
    st.error("⚠️ Файл config.yaml не найден!")
    st.stop()

# Инициализация
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# --- ЕСЛИ УЖЕ ВОШЛИ ---
if st.session_state.get("authentication_status"):
    st.session_state.user_email = st.session_state["username"]
    with st.sidebar:
        # Пытаемся получить имя, если его нет - пишем просто логин
        user_data = config['credentials']['usernames'].get(st.session_state["username"], {})
        user_name = user_data.get('name', st.session_state["username"])
        
        st.write(f"👋 Привет, *{user_name}*!")
        authenticator.logout('Выйти', 'sidebar')

# --- ЕСЛИ НЕ ВОШЛИ ---
else:
    tab_login, tab_reg = st.tabs(["🔑 Вход", "📝 Регистрация"])

   # 1. ВХОД (ПЕРЕВЕДЕН НА РУССКИЙ)
    with tab_login:
        try:
            authenticator.login(
                location='main',
                fields={
                    'username': 'Электронная почта',
                    'password': 'Пароль',
                    'login': 'Войти'
                }
            )
        except Exception as e:
            st.error(e)
            
        if st.session_state["authentication_status"] is False:
            st.error('❌ Неверная почта или пароль')
        elif st.session_state["authentication_status"] is None:
            st.warning('Введите данные для входа')
    # 2. РЕГИСТРАЦИЯ (С ПРЯМЫМ ШИФРОВАНИЕМ ЧЕРЕЗ BCRYPT)
    with tab_reg:
        with st.form("Registration_Form"):
            st.write("Создание нового аккаунта")
            new_email = st.text_input("Электронная почта")
            new_pass = st.text_input("Пароль", type="password")
            new_pass_2 = st.text_input("Подтвердите пароль", type="password")
            submit_reg = st.form_submit_button("Зарегистрироваться")

        if submit_reg:
            if not new_email or not new_pass:
                st.error("❌ Заполните все поля!")
            elif new_pass != new_pass_2:
                st.error("❌ Пароли не совпадают!")
            elif new_email in config['credentials']['usernames']:
                st.error("❌ Такая почта уже есть!")
            else:
                try:
                    # !!! ИСПРАВЛЕНИЕ ОШИБКИ HASHER !!!
                    # Используем bcrypt напрямую, это надежнее
                    hashed_bytes = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt())
                    hashed_pass_str = hashed_bytes.decode('utf-8')
                    
                    # Записываем в конфиг
                    config['credentials']['usernames'][new_email] = {
                        'name': new_email,
                        'email': new_email,
                        'password': hashed_pass_str,
                        'failed_login_attempts': 0,
                        'logged_in': False
                    }
                    
                    with open('config.yaml', 'w') as file:
                        yaml.dump(config, file, default_flow_style=False)
                    
                    st.success("✅ Аккаунт создан! Перейдите на вкладку 'Вход'.")
                    
                except Exception as e:
                    st.error(f"Ошибка сохранения: {e}")

    # Стоп
    if not st.session_state.get("authentication_status"):
        st.stop()
# ==============================================================================
# 2. ЯДРО (API) - ИСПРАВЛЕНО ПОД РОТАЦИЮ
# ==============================================================================
@st.cache_resource
def init_neural_core():
    # Проверяем, есть ли ключи вообще
    if not API_KEYS_POOL:
        return False, "Нет ключей в API_KEYS_POOL", None

    try:
        # БЕРЕМ СЛУЧАЙНЫЙ КЛЮЧ ИЗ СПИСКА (Вместо старого MY_API_KEY)
        start_key = random.choice(API_KEYS_POOL)
        genai.configure(api_key=start_key)
        
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = "models/gemini-pro"
        for m in models:
            if 'flash' in m: target = m; break
        return True, target, genai.GenerativeModel(target)
    except Exception as e:
        return False, str(e), None

# !!! ФИНАЛИЗАЦИЯ ИНИЦИАЛИЗАЦИИ ЯДРА !!!
STATUS, MODEL_NAME, MODEL = init_neural_core()

# ==============================================================================
# 3. ДИЗАЙН (MAXIMUM CONTRAST)
# ==============================================================================
def inject_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Outfit:wght@500;800&display=swap');

        /* --- ФОН --- */
        [data-testid="stAppViewContainer"] {
            background-color: #050505;
            background-image: radial-gradient(at 50% 0%, #1a1a2e 0%, #000000 80%);
            color: #ffffff;
        }

        /* --- ШРИФТЫ --- */
        * { font-family: 'Inter', sans-serif; }
        h1, h2, h3, .stButton button { font-family: 'Outfit', sans-serif !important; }

        /* --- ГЛАВНЫЕ ИСПРАВЛЕНИЯ ЗЕРКАЛИРОВАНИЯ --- */
        header { 
            background: transparent !important; 
            z-index: 99; 
        }
        [data-testid="stAppViewContainer"] > div:first-child > div:first-child {
            /* Фикс для Streamlit, предотвращает инверсию цвета */
            background-color: transparent !important;
        }


     /* --- ГЛАВНЫЕ КНОПКИ (ФИНАЛ: МОБИЛЬНЫЕ + АНИМАЦИЯ + ЦЕНТР) --- */
        
        /* 1. БАЗОВЫЙ СТИЛЬ (СПОКОЙНОЕ СОСТОЯНИЕ) */
        div[data-testid="stButton"] > button {
            /* Жесткий фон и цвет для телефонов (Игнорируем тему системы) */
            background-color: #1a1a1a !important; 
            color: #FFFFFF !important; 
            -webkit-text-fill-color: #FFFFFF !important; /* Для Safari */
            
            /* Рамки и форма */
            border: 2px solid #333 !important; 
            border-radius: 15px !important;
            box-shadow: none !important; 
            
            /* Отключаем прозрачность (Фикс Xiaomi/iPhone) */
            opacity: 1 !important;
            isolation: isolate !important;
            
            /* Убираем системные стили */
            -webkit-appearance: none !important;
            appearance: none !important;
            background-image: none !important;
            
            /* РАЗМЕРЫ (Оптимально для Айфона) */
            padding: 5px 5px !important; 
            min-height: 45px !important; 
            height: auto !important;     
            white-space: normal !important; /* Разрешаем тексту переноситься */
            
            /* Шрифт */
            font-weight: 900 !important;
            text-transform: uppercase !important;
            font-size: 16px !important; 
            line-height: 1.2 !important;
            
            /* Центрирование (Чтобы смайлики были ровно) */
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            
            /* Настройка анимации (Плавность) */
            transition: all 0.2s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
            transform: translateZ(0) !important; /* Стабильность в покое */
        }

        /* Фикс для текста внутри (убираем отступы) */
        div[data-testid="stButton"] > button p {
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.2 !important;
        }

        /* Фикс для серых кнопок (чтобы не были белыми на светлой теме) */
        div[data-testid="stButton"] > button[kind="secondary"] {
            background-color: #1a1a1a !important;
            color: #FFFFFF !important;
        }

        /* Стиль первой кнопки (как на скриншоте - выделенная) */
        div[data-testid="stButton"]:first-child > button {
             background-color: #1a1a1a !important; 
             border: 2px solid #444 !important;
        }

        /* Стиль остальных кнопок */
        div[data-testid="stButton"]:not(:first-child) > button {
            background-color: rgba(255, 255, 255, 0.05) !important; 
            border: 2px solid #333 !important;
            color: #FFFFFF !important; 
        }

        /* 2. ПРИ НАВЕДЕНИИ (АНИМАЦИЯ ВКЛЮЧАЕТСЯ ТУТ) */
        div[data-testid="stButton"] > button:hover {
            border-color: #00E5FF !important;
            color: #000000 !important; /* Черный текст при наведении */
            -webkit-text-fill-color: #000000 !important;
            background-color: #00E5FF !important;
            
            box-shadow: 0 5px 15px rgba(0, 229, 255, 0.2) !important;
            
            /* ВОЗВРАЩАЕМ ДВИЖЕНИЕ */
            transform: translateY(-3px) scale(1.02) !important; 
        }

        /* 3. ПРИ НАЖАТИИ (ЭФФЕКТ ВДАВЛИВАНИЯ) */
        div[data-testid="stButton"] > button:active {
            border-color: #0099CC !important;
            background-color: #0099CC !important;
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            
            /* Сжимаем кнопку */
            transform: scale(0.95) !important;
        }
        /* --- ТЕКСТ ИИ В ЧАТЕ (БЕЛЫЙ) --- */
        [data-testid="stChatMessageContent"] p, 
        [data-testid="stChatMessageContent"] li, 
        [data-testid="stChatMessageContent"] div {
            color: #FFFFFF !important;
            line-height: 1.6;
        }

        /* --- ЧАТ СООБЩЕНИЯ --- */
        [data-testid="stChatMessage"] { background: transparent; padding: 0; margin-bottom: 20px; }

        [data-testid="stChatMessage"][data-test-actor="assistant"] div[data-testid="stChatMessageContent"] {
            background: #161616;
            border: 1px solid #333;
            border-radius: 0 20px 20px 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }

        [data-testid="stChatMessage"][data-test-actor="user"] div[data-testid="stChatMessageContent"] {
            background: rgba(0, 229, 255, 0.1);
            border: 1px solid rgba(0, 229, 255, 0.2);
            border-radius: 20px 0 20px 20px;
        }

        /* --- ПОЛЕ ВВОДА --- */
        [data-testid="stChatInput"] {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 40px 0 50px 0;
            background: linear-gradient(to top, #000000 95%, transparent 100%);
            z-index: 999;
            display: flex;
            justify-content: center;
        }

        .stChatInput > div {
            width: 50% !important; 
            min-width: 400px;
            max-width: 800px;
        }

        .stChatInput textarea {
            background-color: #111 !important;
            color: #ffffff !important;
            caret-color: #00E5FF !important;
            border: 2px solid #333 !important;
            border-radius: 60px !important;
            padding: 18px 30px !important;
            font-size: 16px !important;
            box-shadow: 0 10px 40px rgba(0,0,0,0.8);
        }
        .stChatInput textarea:focus {
            border-color: #00E5FF !important;
            box-shadow: 0 0 25px rgba(0, 229, 255, 0.25) !important;
        }

        /* --- ОСТАЛЬНОЕ (САЙДБАР) --- */
        .stTabs [data-baseweb="tab"] { color: #FFFFFF !important; opacity: 0.6; font-weight: 600; }
        .stTabs [aria-selected="true"] { color: #00E5FF !important; opacity: 1; border-bottom-color: #00E5FF !important; }

        [data-testid="stSidebar"] { 
            background-color: #1a1a1a; 
            border-right: 1px solid #333; 
            color: #ffffff;
        }
        [data-testid="stSidebar"] * {
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #00E5FF !important;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:first-child {
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }


        [data-testid="stSidebarCollapsedControl"] { color: #FFFFFF !important; background-color: rgba(255,255,255,0.1); border-radius: 50%; padding: 4px; }

        [data-testid="stSidebar"] .stButton button {
            background-color: #333 !important;
            border: 1px solid #555 !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            text-shadow: none !important;
            box-shadow: none !important;
        }
        [data-testid="stSidebar"] .stButton button:hover {
            background-color: #00E5FF !important;
            color: #000 !important;
            border-color: #00E5FF !important;
        }

        .stSlider p { color: #FFFFFF !important; font-weight: 700; text-shadow: 0 0 10px rgba(0, 229, 255, 0.4); }
        div[data-testid="stTickBarMin"], div[data-testid="stTickBarMax"] { color: #00E5FF !important; font-weight: bold; }
        div[data-testid="stThumbValue"] { background-color: #FFFFFF !important; color: #000 !important; border: 2px solid #00E5FF; }
        div[data-testid="stSlider"] > div > div > div > div { background: linear-gradient(90deg, #00E5FF, #2979FF) !important; }

        .main .block-container { padding-bottom: 180px; }
        #MainMenu, footer {visibility: hidden;}


        /* Кнопка входа (Гугл) */
        .login-button {
            position: absolute;
            top: 25px;
            right: 25px;
            z-index: 1000;
        }
        .login-button button {
            background: #4285F4 !important; 
            border: 1px solid #4285F4 !important;
            border-radius: 10px !important;
            color: #ffffff !important;
            padding: 8px 15px !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2) !important;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .login-button button:hover {
            background: #3c78d8 !important;
            color: #ffffff !important;
            border-color: #3c78d8 !important;
        }

        .google-icon {
             font-size: 18px;
             line-height: 1;
        }

        .thinking-pulse {
            padding: 10px 20px;
            background: rgba(0, 229, 255, 0.05);
            border: 1px dashed #00E5FF;
            border-radius: 20px;
            color: #00E5FF;
            text-align: center;
            font-family: monospace;
            animation: pulse 1.5s infinite;
            font-size: 12px;
            width: fit-content;
        }
        @keyframes pulse { 0% {opacity: 0.5;} 50% {opacity: 1;} 100% {opacity: 0.5;} }

        .glass-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid #333;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 15px;
        }
    </style>
    """, unsafe_allow_html=True)


inject_css()



# ==============================================================================
# 4. ДАННЫЕ (БАЗА И СПИСКИ) + МОЗГ (AI ENGINE)
# ==============================================================================
def get_features():
    return ["Сладость", "Кислинка", "Тесто", "Шоколад", "Орехи", "Мед", "Ягоды", "Крем", "Алкоголь", "Пряности",
            "Легкость"]


def get_data():
    return [
        {"name": "Медовик", "desc": "Медовые коржи, сметанный крем.", "scores": [8, 3, 7, 0, 2, 10, 0, 8, 0, 1, 4]},
        {"name": "Наполеон", "desc": "Слоеное тесто, заварной крем.", "scores": [6, 0, 9, 0, 2, 0, 0, 9, 0, 0, 3]},
        {"name": "Брауни", "desc": "Шоколадный бисквит, влажный центр.", "scores": [8, 0, 8, 10, 6, 0, 0, 2, 1, 1, 1]},
        {"name": "Чизкейк", "desc": "Сливочный сыр, песочная основа.", "scores": [6, 2, 4, 1, 2, 0, 2, 10, 0, 1, 5]},
        {"name": "Пахлава", "desc": "Орехи, тесто фило, мед.", "scores": [10, 0, 8, 0, 10, 9, 0, 0, 0, 3, 1]},
        {"name": "Ром-Баба", "desc": "Кекс с ромовой пропиткой.", "scores": [9, 0, 9, 0, 1, 0, 3, 2, 10, 2, 3]},
        {"name": "Макаронс", "desc": "Миндальное печенье.", "scores": [7, 6, 3, 2, 8, 0, 9, 5, 0, 0, 6]},
        {"name": "Тирамису", "desc": "Кофе, маскарпоне.", "scores": [5, 1, 4, 4, 1, 0, 0, 9, 3, 1, 7]},
        {"name": "Тарталетка", "desc": "Ягоды и крем.", "scores": [6, 8, 6, 0, 1, 0, 10, 5, 0, 0, 6]},
        {"name": "Крем-Брюле", "desc": "Карамельная корочка.", "scores": [7, 0, 0, 0, 0, 1, 0, 10, 1, 1, 8]},
        {"name": "Эстерхази", "desc": "Безе и орехи.", "scores": [9, 0, 5, 1, 10, 0, 0, 8, 2, 2, 4]},
        {"name": "Панна-Котта", "desc": "Сливочное желе.", "scores": [5, 0, 0, 0, 0, 0, 4, 9, 0, 1, 10]},
        {"name": "Морковный Торт", "desc": "Пряный бисквит.", "scores": [6, 1, 8, 0, 6, 2, 1, 7, 0, 9, 4]},
        {"name": "Канноли", "desc": "Хрустящие трубочки.", "scores": [7, 1, 9, 2, 4, 1, 3, 8, 1, 2, 4]},
        {"name": "Чак-Чак", "desc": "Тесто в меду.", "scores": [9, 0, 9, 0, 1, 10, 0, 0, 0, 0, 2]},
        {"name": "Лимонный Пай", "desc": "Меренга и лимон.", "scores": [7, 9, 6, 0, 0, 0, 2, 4, 0, 0, 5]},
        {"name": "Три Шоколада", "desc": "Муссовый торт.", "scores": [8, 0, 1, 10, 1, 0, 0, 9, 1, 0, 9]},
        {"name": "Зефир", "desc": "Яблочное пюре.", "scores": [8, 5, 0, 0, 0, 0, 6, 0, 0, 1, 10]},
        {"name": "Пряник", "desc": "Имбирное тесто.", "scores": [8, 0, 10, 1, 1, 3, 0, 0, 0, 10, 1]},
        {"name": "Фруктовый Салат", "desc": "Свежесть.", "scores": [4, 7, 2, 0, 1, 2, 10, 0, 0, 0, 8]}
    ]


FEATURES = get_features()
DB = get_data()

# --- СПИСКИ ДЛЯ РАНДОМА ---
RANDOM_RECIPES = ["Предложи рецепт редкого французского десерта.", "Дай рецепт десерта из японской кухни.",
                  "Как приготовить идеальный итальянский Тирамису?",
                  "Рецепт современного муссового торта с зеркальной глазурью.", "Быстрый рецепт десерта за 15 минут.",
                  "Рецепт безглютенового шоколадного фондана.", "Что-то необычное из молекулярной кухни для дома.",
                  "Рецепт классического австрийского штруделя.", "Рецепт португальского Паштел-де-ната.",
                  "Как сделать настоящий турецкий рахат-лукум?", "Рецепт испанского чуррос с шоколадом.",
                  "Секретный рецепт бабушкиного пирога с яблоками.", "Рецепт торта 'Красный бархат' в оригинале.",
                  "Десерт Павлова: как сделать идеально белым?", "Рецепт профитролей с кракелюром.",
                  "Как сделать домашнее мороженое без мороженицы?", "Рецепт фисташкового рулета с малиной.",
                  "Баскский чизкейк (Сан-Себастьян) - рецепт.", "Рецепт английского трайфла с ягодами.",
                  "Десерт 'Плавающий остров' (Ile Flottante)."]
RANDOM_FACTS = ["Расскажи неочевидный факт из истории шоколада.", "Почему сахарная вата такая пушистая? Факт.",
                "Самый дорогой десерт в мире? Факт.", "Как появилось мороженое? Краткий факт.",
                "В какой стране едят больше всего сладкого?", "Химический факт: почему карамель коричневая?",
                "Откуда пошло название торта 'Наполеон'?", "Правда ли, что белый шоколад - это не шоколад?",
                "Какой десерт был любимым у Марии Антуанетты?", "История появления круассана (это не Франция!).",
                "Почему марципан так называется?", "Сколько слоев должно быть в идеальном Мильфее?",
                "Факт про самое большое печенье в мире.", "Почему пончики имеют дырку посередине?",
                "Какой десерт подают на Нобелевском банкете?", "История тирамису: правда или миф про публичные дома?",
                "Почему ваниль такая дорогая?", "Факт про шоколадную фабрику Вилли Вонки (реальную).",
                "Что такое 'золотой' шоколад?", "Как придумали чупа-чупс?"]
RANDOM_PAIRINGS = ["С чем идеально сочетается малина в десертах?", "Лучшие компаньоны для темного шоколада.",
                   "Необычные сочетания с соленой карамелью.", "Что добавить к ванили, чтобы раскрыть вкус?",
                   "Сочетание базилика и клубники - почему это работает?", "Специи для яблочного пирога, кроме корицы.",
                   "С чем сочетать манго в муссовых тортах?", "Кофе и десерты: правила идеальной пары.",
                   "С чем подавать голубой сыр в десертах?", "Неожиданные пары: шоколад и бекон?",
                   "С чем сочетается лаванда в выпечке?", "Лучшие орехи для морковного торта.",
                   "Алкоголь в десертах: что к чему подходит?", "Сочетание мяты и шоколада: за и против.",
                   "С чем сочетать кокос, кроме ананаса?", "Идеальная пара для груши (кроме сыра).",
                   "С чем сочетается матча?", "Фисташка и малина: почему это классика?",
                   "Чем оттенить вкус белого шоколада?", "Сочетание розмарина и апельсина."]
RANDOM_TIPS = ["Секрет идеальной меренги, чтобы она не опала.", "Как темперировать шоколад в домашних условиях?",
               "Почему бисквит оседает? Совет шефа.", "Как сделать песочное тесто рассыпчатым?",
               "Лайфхак для взбивания сливок.", "Как спасти перевзбитый ганаш?",
               "Как сделать зеркальную глазурь без пузырей?", "Секрет сочных кексов: что добавить?",
               "Как правильно растопить шоколад, чтобы не свернулся?",
               "Почему нельзя открывать духовку при выпечке бисквита?",
               "Как сделать карамель, которая не кристаллизуется?", "Совет по работе с желатином и агаром.",
               "Как сделать идеально ровный торт?", "Секрет хрустящей корочки у эклеров.",
               "Как быстро размягчить сливочное масло?", "Как проверить готовность выпечки без зубочистки?",
               "Совет по окрашиванию крема в яркие цвета.", "Как хранить макаронс, чтобы они стали вкуснее?",
               "Что делать, если крем расслоился?", "Как аккуратно нарезать торт?"]

# --- СПИСОК РУГАТЕЛЬСТВ ДЛЯ ШЕФА (СЕРИАЛ КУХНЯ) ---
CHEF_INSULTS = [
    "СЛУШАЙ СЮДА, ОГУЗОК! ",
    "ТЫ ВООБЩЕ ЧЕМ ДУМАЛ, ИУДА?! ",
    "ИНФУЗОРИЯ С ПОЛОВНИКОМ, БЫСТРО СЮДА! ",
    "ТЫ ПЫТАЕШЬСЯ ОТРАВИТЬ МОИХ ГОСТЕЙ?! ",
    "УБЕРИ СВОИ КРИВЫЕ РУКИ ОТ ПРОДУКТОВ! ",
    "ЭТО ЧТО ЗА ПОЗОР НА МОЕЙ КУХНЕ?! ",
    "ТЫ НЕ ПОВАР, ТЫ ВРЕДИТЕЛЬ! ",
    "БЫСТРЕЕ, ОВОЩ, ПОКА Я ТЕБЯ НЕ НАШИНКОВАЛ! "
]


# --- УМНЫЙ AI ENGINE (С НАРАСТАЮЩЕЙ ЗЛОСТЬЮ) ---
def ai_engine(history, prompt, mode):
    if not STATUS: return "⚠ Ошибка связи с ядром."
    try:
        # 1. ЛОГИКА ШЕФА (ДИНАМИЧЕСКАЯ)
        if mode == "CHEF":
            # Считаем, сколько раз пользователь уже спросил (длину истории делим на 2)
            # Чем больше вопросов, тем злее Шеф
            annoyance_level = len(history) // 2

            if annoyance_level < 3:
                # СТАДИЯ 1: Просто строгий (Ворчит, но не орет)
                sys_prompt = "ТЫ СТРОГИЙ ШЕФ-КОНДИТЕР. Ты занят делом. Тебе некогда болтать. Отвечай сухо, четко, профессионально, но с ноткой недовольства, что тебя отвлекают. Не используй капслок. Обращайся на ТЫ."
                hidden_instruction = " (Ответь строго и сухо. Ты занят. Дай информацию, но покажи, что у тебя мало времени. Без ругани.)"

            elif annoyance_level < 6:
                # СТАДИЯ 2: Раздражение (Начинает обзываться)
                sys_prompt = "ТЫ РАЗДРАЖЕННЫЙ ШЕФ. Тебя достали глупые вопросы. Используй слова 'Огузок', 'Лентяй'. Добавь сарказма. Можешь выделить ОДНО важное слово капслоком. Ты начинаешь злиться."
                hidden_instruction = " (Ответь с раздражением и сарказмом. Назови пользователя Огузком. Ты теряешь терпение. Дай рецепт, но поворчи.)"

            else:
                # СТАДИЯ 3: ЯРОСТЬ (Виктор Баринов)
                random_insult = random.choice(CHEF_INSULTS)
                sys_prompt = f"ТЫ В ЯРОСТИ. Твое терпение лопнуло. Ты кричишь (используй капслок в начале). Называй пользователя 'ИУДА', 'ИНВАЛИД'. Начни ответ с фразы: **{random_insult}**. Но в конце все же дай ответ, чтобы он отстал."
                hidden_instruction = f" (ТЫ В БЕШЕНСТВЕ! НАЧНИ С КРИКА И РУГАНИ! Но информацию все равно дай, чтобы он ушел с кухни.)"

        # 2. ДОБРЯЧОК
        elif mode == "KIND":
            sys_prompt = "ТЫ МИЛЫЙ ПОМОЩНИК. Твой тон — теплый и заботливый. НЕ ЗДОРОВАЙСЯ ЗАНОВО. Используй смайлики (✨, 🍰)."
            hidden_instruction = " (ВАЖНО: БУДЬ МИЛЫМ! ПИШИ ОТ МУЖСКОГО РОДА (например, 'я сделал', 'я рад'), ЕСЛИ НЕ ПРОСИЛИ В ЖЕНСКОМ! НЕ ЗДОРОВАЙСЯ ПОВТОРНО, ПРОСТО ОТВЕТЬ С ТЕПЛОТОЙ!)"

        # 3. АССИСТЕНТ
        else:
            sys_prompt = "ТЫ VLADЫКА AI. Умный, профессиональный помощник. Твой тон — вежливый, спокойный, с легкой долей эмоций."
            hidden_instruction = " (ВАЖНО: ОТВЕТЬ ВЕЖЛИВО И ПРОФЕССИОНАЛЬНО. БУДЬ ДРУЖЕЛЮБЕН, НО СДЕРЖАН.)"

        # Создаем чат
        chat = MODEL.start_chat(history=[{"role": "user", "parts": [sys_prompt]}])

        # Загружаем историю
        for m in history[-6:]:
            role = "user" if m["role"] == "user" else "model"
            chat.history.append({"role": role, "parts": [m["content"]]})

        # Отправляем
        final_prompt = prompt + hidden_instruction
        return chat.send_message(final_prompt).text
    except Exception as e:
        return f"⚠ Error: {e}"
# ==============================================================================
# 5. ИНТЕРФЕЙС
# ==============================================================================
# --- ИНИЦИАЛИЗАЦИЯ ПЕРЕМЕННЫХ ---
if 'history' not in st.session_state: st.session_state.history = []
if 'chats' not in st.session_state: st.session_state.chats = []  # Архив чатов
if 'current_chat_id' not in st.session_state: st.session_state.current_chat_id = None  # ID текущего
if 'mode' not in st.session_state: st.session_state.mode = "AI"
if 'vec' not in st.session_state: st.session_state.vec = [5] * len(FEATURES)
if 'trigger_query' not in st.session_state: st.session_state.trigger_query = None


# --- ФУНКЦИИ УПРАВЛЕНИЯ ЧАТАМИ ---
def save_current_chat():
    """Сохраняет текущую переписку в архив перед сменой чата"""
    if not st.session_state.history:
        return  # Не сохраняем пустые чаты

    # Генерируем название (первые 30 символов)
    title = "Новый диалог"
    for msg in st.session_state.history:
        if msg["role"] == "user":
            title = msg["content"][:25] + "..." if len(msg["content"]) > 25 else msg["content"]
            break

    chat_data = {
        "title": title,
        "history": st.session_state.history,
        "mode": st.session_state.mode
    }

    # Если мы в старом чате - обновляем его
    if st.session_state.current_chat_id is not None:
        if st.session_state.current_chat_id < len(st.session_state.chats):
            st.session_state.chats[st.session_state.current_chat_id] = chat_data
    else:
        # Если это новый чат - добавляем в список
        st.session_state.chats.append(chat_data)
        st.session_state.current_chat_id = len(st.session_state.chats) - 1


def create_new_chat():
    """Начинает новый диалог, предварительно сохранив старый"""
    save_current_chat()  # Сначала в архив
    st.session_state.history = []  # Чистим экран
    st.session_state.current_chat_id = None  # Сбрасываем ID (мы в новом)
    # st.session_state.mode = "AI" # Можно сбросить режим на Ассистента, если хотите


def load_chat(index):
    """Загружает чат из архива"""
    save_current_chat()  # Сохраняем текущий перед уходом
    st.session_state.history = st.session_state.chats[index]["history"]
    st.session_state.mode = st.session_state.chats[index].get("mode", "AI")
    st.session_state.current_chat_id = index


def clear_archives_only():
    """Удаляет ТОЛЬКО историю (архив), но оставляет текущий экран чистым"""
    st.session_state.chats = []  # Удаляем архив
    st.session_state.current_chat_id = None  # Отвязываемся от ID
    st.session_state.history = []  # Очищаем текущий экран для старта


# Функция для принудительного скролла
def scroll_to_end(delay=100):
    components.html(f"""
        <script>
            setTimeout(() => {{
                const endChatElement = window.parent.document.getElementById('end-chat');
                if (endChatElement) {{
                    endChatElement.scrollIntoView({{behavior: "smooth", block: "end"}});
                }}
            }}, {delay}); 
        </script>
        """, height=0)


# !!! КНОПКА ВХОДА !!!
st.markdown("""
<div class="login-button">
    <button onclick="window.parent.alert('Функционал входа через Google пока не реализован!')">
        <span class="google-icon">G</span> Войти
    </button>
</div>
""", unsafe_allow_html=True)

# --- САЙДБАР (С ДОБРЯЧКОМ) ---
with st.sidebar:
    st.title("⚙️ МЕНЮ")

    # 1. Большая кнопка НОВЫЙ ЧАТ
    if st.button("📝 НАЧАТЬ НОВЫЙ ЧАТ", use_container_width=True):
        create_new_chat()
        st.rerun()

    st.divider()

    st.write("### РЕЖИМ")

    # 1. Определяем, где должна стоять точка (0=Ассистент, 1=Шеф, 2=Добрячок)
    current_idx = 0
    if st.session_state.mode == "CHEF":
        current_idx = 1
    elif st.session_state.mode == "KIND":
        current_idx = 2

    # 2. Рисуем кнопку с тремя вариантами
    selected_option = st.radio(
        "",
        ["Ассистент", "Шеф-Повар", "Добрячок"],  # <--- Добавили Добрячка
        index=current_idx,
        label_visibility="collapsed",
        key="mode_radio_widget"
    )

    # 3. Вычисляем, какой режим выбрал пользователь
    target_mode = "AI"  # По умолчанию Ассистент
    if selected_option == "Шеф-Повар":
        target_mode = "CHEF"
    elif selected_option == "Добрячок":
        target_mode = "KIND"

    # Если то, что на кнопке, отличается от того, что в мозгах бота:
    if target_mode != st.session_state.mode:
        # 1. Меняем режим в памяти
        st.session_state.mode = target_mode
        # 2. Сохраняем это состояние в текущий чат
        save_current_chat()

        # Уведомление о смене (чтобы было видно, что сработало)
        if target_mode == "CHEF":
            st.toast("👨‍🍳 Режим: Ворчливый Шеф")
        elif target_mode == "KIND":
            st.toast("💛 Режим: Добрячок")
        else:
            st.toast("🤖 Режим: Ассистент")

        # 3. ПРИНУДИТЕЛЬНО перезагружаем страницу
        st.rerun()

    st.divider()

    # 2. СПИСОК ЧАТОВ
    st.write("### 🗂 АРХИВ")
    if not st.session_state.chats:
        st.caption("Нет сохраненных диалогов")

    # Выводим (новые сверху)
    for i, chat in reversed(list(enumerate(st.session_state.chats))):
        label = f"💬 {chat['title']}"
        type_btn = "secondary"
        if i == st.session_state.current_chat_id:
            label = f"🟢 {chat['title']}"  # Визуально помечаем текущий
            type_btn = "primary"  # Выделяем цветом

        if st.button(label, key=f"chat_btn_{i}", use_container_width=True, type=type_btn):
            load_chat(i)
            st.rerun()

    st.divider()

    # 3. КНОПКА УДАЛИТЬ АРХИВ
    if st.button("🗑 УДАЛИТЬ ИСТОРИЮ", use_container_width=True):
        clear_archives_only()
        st.rerun()
# --- ТАБЫ ---
t1, t2, t3 = st.tabs(["💬 ЧАТ", "🎛 ВКУСЫ", "📂 БАЗА"])

# --- ЧАТ ---
with t1:
    st.markdown(
        "<h1 style='text-align: center; margin-bottom: 30px;'>Vladыка <span style='color:#00E5FF'>AI</span></h1>",
        unsafe_allow_html=True)


    # --- МОБИЛЬНАЯ АДАПТАЦИЯ КНОПОК (2x2) ---
    # Вместо 4 колонок делаем 2 ряда по 2 колонки

    def set_query(q):
        st.session_state.history.append({"role": "user", "content": q})
        st.session_state.trigger_rerun = True


    # Первый ряд кнопок
    row1_1, row1_2 = st.columns(2)
    row1_1.button("🎲 СЛУЧАЙНЫЙ ФАКТ", on_click=set_query, args=(random.choice(RANDOM_FACTS),), use_container_width=True)
    row1_2.button("📜 РАНДОМ РЕЦЕПТ", on_click=set_query, args=(random.choice(RANDOM_RECIPES),),
                  use_container_width=True)

    # Второй ряд кнопок
    row2_1, row2_2 = st.columns(2)
    row2_1.button("🍷 СОЧЕТАНИЯ", on_click=set_query, args=(random.choice(RANDOM_PAIRINGS),), use_container_width=True)
    row2_2.button("💡 ПОЛЕЗНЫЙ СОВЕТ", on_click=set_query, args=(random.choice(RANDOM_TIPS),), use_container_width=True)

    # Логика перезагрузки после кнопок
    if 'trigger_rerun' in st.session_state and st.session_state.trigger_rerun:
        st.session_state.trigger_rerun = False
        scroll_to_end(delay=10)
        st.rerun()

    st.write("")

    # Вывод сообщений
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Якорь для скролла
    st.markdown("<div id='end-chat'></div>", unsafe_allow_html=True)

    # --- ЛОГИКА ВВОДА И ОТВЕТА ---
    prompt = None

    if input_val := st.chat_input("Введите сообщение..."):
        prompt = input_val
        st.session_state.history.append({"role": "user", "content": prompt})
        st.rerun()

    if st.session_state.history and st.session_state.history[-1]["role"] == "user":
        scroll_to_end(delay=10)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("""<div class="thinking-pulse">⚡ ГЕНЕРАЦИЯ ОТВЕТА...</div>""", unsafe_allow_html=True)

            last_user_msg = st.session_state.history[-1]["content"]
            current_mode = st.session_state.mode

            # Генерируем ответ
            resp = ai_engine(st.session_state.history[:-1], last_user_msg, current_mode)
            placeholder.empty()
            st.markdown(resp)

        st.session_state.history.append({"role": "assistant", "content": resp})

        # АВТОСОХРАНЕНИЕ
        save_current_chat()

        scroll_to_end(delay=300)

# --- ВЕКТОРЫ (БЕЗ ИЗМЕНЕНИЙ) ---
with t2:
    st.header("🧬 ПОДБОР ВКУСА")
    c_sl, c_res = st.columns([1, 1.5])

    if 'vec' not in st.session_state or len(st.session_state.vec) != len(FEATURES):
        st.session_state.vec = [5] * len(FEATURES)

    with c_sl:
        new_vec = []
        for i, f in enumerate(FEATURES):
            val = st.slider(f, 0, 10, st.session_state.vec[i], key=f"slider_{i}")
            new_vec.append(val)
        st.session_state.vec = new_vec

    with c_res:
        st.subheader("⚡ ЛУЧШИЕ ВАРИАНТЫ")
        res = []
        for d in DB:
            diff = sum([abs(a - b) for a, b in zip(new_vec, d['scores'])])
            max_diff = len(FEATURES) * 10
            score = max(0, int((1 - diff / max_diff) * 100))
            res.append((d, score))

        res.sort(key=lambda x: x[1], reverse=True)

        for item, sc in res[:4]:
            color = "#00E5FF" if sc > 80 else "#aaa"
            st.markdown(f"""
            <div class="glass-card" style="border-left: 5px solid {color}">
                <div style="display:flex; justify-content:space-between;">
                    <h3 style="margin:0">{item['name']}</h3>
                    <h2 style="margin:0; color:{color}">{sc}%</h2>
                </div>
                <p>{item['desc']}</p>
                <div style="background:#333; height:8px; width:100%; border-radius:4px; margin-top:10px;">
                    <div style="background: linear-gradient(90deg, #00E5FF, #2979FF); width:{sc}%; height:100%; border-radius:4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# --- БАЗА (БЕЗ ИЗМЕНЕНИЙ) ---
with t3:
    st.header("📂 БАЗА ДАННЫХ")
    df = pd.DataFrame(DB)
    sc = pd.DataFrame(df['scores'].tolist(), columns=FEATURES)
    st.dataframe(pd.concat([df[['name', 'desc']], sc], axis=1), use_container_width=True)





















