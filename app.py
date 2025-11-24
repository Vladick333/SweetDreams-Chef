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
# =================================================================
# =================================================================
# !!! БЛОК 0: ГАРАНТИРОВАННЫЙ TOAST (САМЫЙ ВЕРХ СКРИПТА) !!!
# =================================================================
if 'show_login_toast_flag' in st.session_state and st.session_state['show_login_toast_flag']:
    st.toast("⬅ Нажмите на стрелочку меню слева для входа", icon="👉")
    # Очищаем флаг, чтобы Toast не появлялся снова
    del st.session_state['show_login_toast_flag']

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
# 1.2. АВТОРИЗАЦИЯ (КРАСИВЫЙ ДИЗАЙН + ВЕЧНАЯ ПАМЯТЬ В ФАЙЛЕ)
# ==============================================================================
import streamlit_authenticator as stauth
import bcrypt 
import json
import os

# --- ФАЙЛ БАЗЫ ПОЛЬЗОВАТЕЛЕЙ ---
USERS_FILE = "users.json"

# Загрузка пользователей с диска
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

# Сохранение пользователей на диск
def save_users(users_data):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка сохранения юзеров: {e}")


# 1. НАСТРОЙКИ (ЗАГРУЖАЕМ ПРИ СТАРТЕ)
if 'auth_config' not in st.session_state:
    hashed_pass = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
    
    # 1. Грузим из файла
    saved_users = load_users()
    
    # 2. Добавляем Админа (если его нет в файле)
    if 'admin' not in saved_users:
        saved_users['admin'] = { 
            'name': 'Владыка',
            'password': hashed_pass, 
            'email': 'admin@gmail.com',
        }
    
    st.session_state.auth_config = {
        'credentials': {
            'usernames': saved_users
        }
    }

# --- ФУНКЦИЯ ДЛЯ КРАСИВЫХ ЗАГОЛОВКОВ ---
def custom_header(text):
    st.markdown(f"""
    <h2 style="
        color: #00E5FF; 
        font-family: 'Outfit', sans-serif; 
        font-weight: 800; 
        border: none; 
        padding: 0; 
        margin-bottom: 10px;
        margin-top: 0;
    ">{text}</h2>
    """, unsafe_allow_html=True)

# 3. ОТРИСОВКА В САЙДБАРЕ
with st.sidebar:

    # ЕСЛИ ПОЛЬЗОВАТЕЛЬ ВОШЕЛ
    if st.session_state.get("authentication_status"):
        user_name = st.session_state['name']
        st.markdown(f"""
        <div style="
            padding: 15px;
            border-radius: 12px;
            border: 1px solid rgba(0, 229, 255, 0.3);
            background: rgba(0, 229, 255, 0.05);
            color: #ffffff;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        ">
            <div style="font-size: 28px;">👤</div>
            <div style="line-height: 1.2;">
                <div style="font-size: 12px; color: rgba(255,255,255,0.5); font-weight: 600;">ВЫ ВОШЛИ КАК</div>
                <div style="font-size: 18px; font-weight: 800; color: #00E5FF; letter-spacing: 0.5px;">{user_name}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Выйти", use_container_width=True):
            st.session_state["authentication_status"] = None
            st.session_state["username"] = None
            st.rerun()

        st.session_state.user_email = st.session_state["username"]

    # ЕСЛИ НЕ ВОШЕЛ  ← ВЕРНУТО ВНУТРЬ sidebar!!!
    else:
        st.info("👀 Вы в режиме **Гостя**")

        with st.expander(
            "🔐 Вход / Регистрация",
            expanded=st.session_state.get("force_open_login", False)
        ):
            tab_login, tab_reg = st.tabs(["Вход", "Создать"])



            # --- ВХОД ---
            with tab_login:
                custom_header("Вход в систему")
                with st.form("LoginForm"):
                    login_user = st.text_input("Почта")
                    login_pass = st.text_input("Пароль", type="password")
                    btn_login = st.form_submit_button("Войти", use_container_width=True)
                
                if btn_login:
                    users = st.session_state.auth_config['credentials']['usernames']
                    if login_user in users:
                        stored_hash = users[login_user]['password']
                        if bcrypt.checkpw(login_pass.encode('utf-8'), stored_hash.encode('utf-8')):
                            st.session_state["authentication_status"] = True
                            st.session_state["username"] = login_user
                            st.session_state["name"] = users[login_user]['name']
                            st.toast("✅ Успешный вход!")
                            st.rerun()
                        else:
                            st.error("Неверный пароль")
                    else:
                        st.error("Пользователь не найден")

            # --- РЕГИСТРАЦИЯ (С СОХРАНЕНИЕМ В ФАЙЛ) ---
            with tab_reg:
                custom_header("Новый пользователь")
                with st.form("RegForm"):
                    new_user = st.text_input("Введите Почту")
                    new_name = st.text_input("Ваше Имя")
                    new_pass = st.text_input("Пароль", type="password")
                    rep_pass = st.text_input("Повторите пароль", type="password")
                    btn_reg = st.form_submit_button("Зарегистрироваться", use_container_width=True)
                    
                    if btn_reg:
                        if not (new_user and new_name and new_pass):
                            st.error("Заполните все поля!")
                        elif new_pass != rep_pass:
                            st.error("Пароли не совпадают!")
                        elif new_user in st.session_state.auth_config['credentials']['usernames']:
                            st.error("Такая почта уже есть!")
                        else:
                            try:
                                hashed_pw = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                
                                # 1. Сохраняем в память
                                st.session_state.auth_config['credentials']['usernames'][new_user] = {
                                    'name': new_name,
                                    'password': hashed_pw,
                                    'email': new_user
                                }
                                
                                # 2. СОХРАНЯЕМ В ФАЙЛ (ВЕЧНОСТЬ)
                                save_users(st.session_state.auth_config['credentials']['usernames'])
                                
                                st.success("✅ Аккаунт создан! Теперь войдите.")
                            except Exception as e:
                                st.error(f"Ошибка: {e}")

# Если не вошел - пускаем как гостя
if not st.session_state.get("authentication_status"):
    st.session_state.user_email = "Гость"
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
# 5. ИНТЕРФЕЙС (ФИНАЛ: КНОПКА V РАСКРЫВАЕТ ВХОД)
# ==============================================================================
import json
import os
import streamlit.components.v1 as components

# --- ФУНКЦИИ ПАМЯТИ ---
def get_history_filename():
    username = st.session_state.get("username", "guest")
    safe_name = "".join([c for c in username if c.isalnum() or c in (' ', '_', '-')]).strip()
    return f"history_{safe_name}.json"

def load_history():
    if not st.session_state.get("authentication_status"): return []
    filename = get_history_filename()
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_history():
    if not st.session_state.get("authentication_status"): return
    filename = get_history_filename()
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(st.session_state.chats, f, ensure_ascii=False, indent=4)
    except Exception as e: print(f"Ошибка сохранения: {e}")

# --- ИНИЦИАЛИЗАЦИЯ ---
if 'last_logged_user' not in st.session_state:
    st.session_state.last_logged_user = st.session_state.get("username", "guest")

current_user = st.session_state.get("username", "guest")
if current_user != st.session_state.last_logged_user:
    st.session_state.last_logged_user = current_user
    st.session_state.chats = load_history()
    st.session_state.history = []
    st.session_state.current_chat_id = None

if 'chats' not in st.session_state: st.session_state.chats = load_history()
if 'history' not in st.session_state: st.session_state.history = []
if 'current_chat_id' not in st.session_state: st.session_state.current_chat_id = None
if 'mode' not in st.session_state: st.session_state.mode = "AI"
if 'vec' not in st.session_state: st.session_state.vec = [5] * len(FEATURES)
if 'trigger_query' not in st.session_state: st.session_state.trigger_query = None
if 'show_login' not in st.session_state: st.session_state.show_login = False # Флаг для открытия меню


# --- УПРАВЛЕНИЕ ЧАТАМИ ---
def save_current_chat():
    if not st.session_state.history: return
    title = "Новый диалог"
    for msg in st.session_state.history:
        if msg["role"] == "user":
            title = msg["content"][:25] + "..." if len(msg["content"]) > 25 else msg["content"]
            break
    chat_data = {"title": title, "history": st.session_state.history, "mode": st.session_state.mode}
    if st.session_state.current_chat_id is not None:
        if st.session_state.current_chat_id < len(st.session_state.chats):
            st.session_state.chats[st.session_state.current_chat_id] = chat_data
    else:
        st.session_state.chats.append(chat_data)
        st.session_state.current_chat_id = len(st.session_state.chats) - 1
    save_history()

def create_new_chat():
    save_current_chat()
    st.session_state.history = []
    st.session_state.current_chat_id = None

def load_chat(index):
    save_current_chat()
    st.session_state.history = st.session_state.chats[index]["history"]
    st.session_state.mode = st.session_state.chats[index].get("mode", "AI")
    st.session_state.current_chat_id = index

def clear_archives_only():
    st.session_state.chats = []
    st.session_state.current_chat_id = None
    if st.session_state.get("authentication_status"):
        filename = get_history_filename()
        if os.path.exists(filename): os.remove(filename)

def scroll_to_end(delay=100):
    components.html(f"""<script>setTimeout(() => {{const e = window.parent.document.getElementById('end-chat');if(e){{e.scrollIntoView({{behavior: "smooth", block: "end"}});}}}}, {delay});</script>""", height=0)



# =================================================================
# !!! ПЛАВАЮЩАЯ КНОПКА ВХОДА (МАКСИМАЛЬНАЯ ФИКСАЦИЯ) !!!
# =================================================================
if not st.session_state.get("authentication_status"):
    
    # 1. CSS: Крепим кнопку справа сверху (ОЧЕНЬ АГРЕССИВНЫЙ CSS)
    st.markdown("""
    <style>
    /* 1. Нацеливаемся на родительский блок кнопки, чтобы зафиксировать его */
    div[data-testid="stVerticalBlock"] > div > div:nth-child(1) div[data-testid="stHorizontalBlock"] > div:last-child > div.stButton {
        /* ЭТО ДОЛЖНО РЕШИТЬ ПРОБЛЕМУ С ПРОКРУТКОЙ: */
        position: fixed !important; 
        top: 100px !important; /* Фиксируем на удобной высоте */
        right: 20px !important;
        z-index: 99999999 !important; /* МАКСИМАЛЬНЫЙ ПРИОРИТЕТ */
    }
    
    /* 2. Нацеливаемся на саму кнопку для стилей */
    div.stButton > button[kind="primary"] {
        background-color: #4285F4 !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.2rem !important;
        font-weight: bold !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.4) !important;
        /* Убираем конфликты трансформации */
        transform: none !important;
        width: auto !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #357ae8 !important;
        transform: scale(1.05) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 2. Кнопка (При нажатии устанавливает флаги и вызывает JS)
    if st.button("V Войти", key="float_login_btn", type="primary"):
        
        # 1. Устанавливаем флаги Python
        st.session_state['force_open_login'] = True
        st.session_state['show_login_toast_flag'] = True
        
        # 2. АГРЕССИВНЫЙ JS для открытия меню
        components.html("""
        <script>
            // Метод 1: Отправляем сигнал Streamlit
            window.parent.postMessage({
                type: "streamlit:setSidebarState",
                collapsed: false
            }, "*");
        </script>
        """, height=0, width=0)
        
        # 3. Перезагружаем
        st.rerun()
# --- САЙДБАР ---
with st.sidebar:
    st.title("⚙️ МЕНЮ")
    if st.button("📝 НАЧАТЬ НОВЫЙ ЧАТ", use_container_width=True):
        create_new_chat()
        st.rerun()
    st.divider()
    st.write("### РЕЖИМ")
    
    current_idx = 0
    if st.session_state.mode == "CHEF": current_idx = 1
    elif st.session_state.mode == "KIND": current_idx = 2
    
    selected_option = st.radio("", ["Ассистент", "Шеф-Повар", "Добрячок"], index=current_idx, label_visibility="collapsed", key="mode_radio_widget")
    
    target_mode = "AI"
    if selected_option == "Шеф-Повар": target_mode = "CHEF"
    elif selected_option == "Добрячок": target_mode = "KIND"
    
    if target_mode != st.session_state.mode:
        st.session_state.mode = target_mode
        save_current_chat()
        if target_mode == "CHEF": st.toast("👨‍🍳 Режим: Ворчливый Шеф")
        elif target_mode == "KIND": st.toast("💛 Режим: Добрячок")
        else: st.toast("🤖 Режим: Ассистент")
        st.rerun()

    st.divider()
    st.write("### 🗂 АРХИВ")
    if not st.session_state.get("authentication_status"): st.caption("⚠ Гостевой режим")
    if not st.session_state.chats: st.caption("Нет диалогов")
    
    for i, chat in reversed(list(enumerate(st.session_state.chats))):
        label = f"🟢 {chat['title']}" if i == st.session_state.current_chat_id else f"💬 {chat['title']}"
        btn_type = "primary" if i == st.session_state.current_chat_id else "secondary"
        if st.button(label, key=f"chat_{i}", use_container_width=True, type=btn_type):
            load_chat(i)
            st.rerun()

    st.divider()
    if st.button("🗑 УДАЛИТЬ ИСТОРИЮ", use_container_width=True):
        clear_archives_only()
        st.rerun()


# --- 5. ОСНОВНОЙ ЭКРАН ---
t1, t2, t3 = st.tabs(["💬 ЧАТ", "🎛 ВКУСЫ", "📂 БАЗА"])

with t1:
    st.markdown("<h1 style='text-align: center; margin-bottom: 20px;'>Vladыка <span style='color:#00E5FF'>AI</span></h1>", unsafe_allow_html=True)

    def set_query(q):
        st.session_state.history.append({"role": "user", "content": q})
        st.session_state.trigger_rerun = True

    # ТВОЙ ИДЕАЛЬНЫЙ ДИЗАЙН КНОПОК (2x2)
    col_grid = st.columns([1, 1]) 
    
    with col_grid[0]:
        st.button("🎲 СЛУЧАЙНЫЙ ФАКТ", on_click=set_query, args=(random.choice(RANDOM_FACTS),), use_container_width=True)
        st.button("🍷 СОЧЕТАНИЯ", on_click=set_query, args=(random.choice(RANDOM_PAIRINGS),), use_container_width=True)
        
    with col_grid[1]:
        st.button("📜 РАНДОМ РЕЦЕПТ", on_click=set_query, args=(random.choice(RANDOM_RECIPES),), use_container_width=True)
        st.button("💡 СОВЕТ", on_click=set_query, args=(random.choice(RANDOM_TIPS),), use_container_width=True)

    if st.session_state.trigger_query:
        st.session_state.history.append({"role": "user", "content": st.session_state.trigger_query})
        st.session_state.trigger_query = None
        st.rerun()

    if 'trigger_rerun' in st.session_state and st.session_state.trigger_rerun:
        st.session_state.trigger_rerun = False
        scroll_to_end(delay=10)
        st.rerun()

    st.write("") 

    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    st.markdown("<div id='end-chat'></div>", unsafe_allow_html=True)

    if prompt := st.chat_input("Введите сообщение..."):
        st.session_state.history.append({"role": "user", "content": prompt})
        st.rerun()

    if st.session_state.history and st.session_state.history[-1]["role"] == "user":
        scroll_to_end(delay=10)
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("""<div class="thinking-pulse">⚡ ГЕНЕРАЦИЯ ОТВЕТА...</div>""", unsafe_allow_html=True)
            resp = ai_engine(st.session_state.history[:-1], st.session_state.history[-1]["content"], st.session_state.mode)
            placeholder.empty()
            st.markdown(resp)
        
        st.session_state.history.append({"role": "assistant", "content": resp})
        save_current_chat() 
        scroll_to_end(delay=300)


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
            score = max(0, int((1 - diff / (len(FEATURES)*10)) * 100))
            res.append((d, score))
        res.sort(key=lambda x: x[1], reverse=True)

        for item, sc in res[:4]:
            color = "#00E5FF" if sc > 80 else "#aaa"
            st.markdown(f"""
            <div class="glass-card" style="border-left: 5px solid {color}">
                <div style="display:flex; justify-content:space-between;"><h3 style="margin:0">{item['name']}</h3><h2 style="margin:0; color:{color}">{sc}%</h2></div>
                <p>{item['desc']}</p>
                <div style="background:#333; height:8px; width:100%; border-radius:4px; margin-top:10px;"><div style="background: linear-gradient(90deg, #00E5FF, #2979FF); width:{sc}%; height:100%; border-radius:4px;"></div></div>
            </div>""", unsafe_allow_html=True)


with t3:
    st.header("📂 БАЗА ДАННЫХ")
    df = pd.DataFrame(DB)
    sc = pd.DataFrame(df['scores'].tolist(), columns=FEATURES)
    st.dataframe(pd.concat([df[['name', 'desc']], sc], axis=1), use_container_width=True)



























































