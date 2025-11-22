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

# ==============================================================================
# 1. НАСТРОЙКИ
# ==============================================================================
st.set_page_config(
    page_title="Vladыка AI [v24.0]",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# !!! БЕЗОПАСНОЕ ЧТЕНИЕ КЛЮЧА API !!!
try:
    # Пытаемся получить ключ из переменной "GEMINI_API_KEY" из Streamlit Secrets
    MY_API_KEY = st.secrets["GEMINI_API_KEY"] 
except KeyError:
    # Если ключ не найден (KeyError), присваиваем заглушку и показываем ошибку
    MY_API_KEY = "PLACEHOLDER_KEY_REQUIRED_FOR_CLOUD_DEPLOYMENT" 
    st.error("⚠️ Ошибка: Ключ GEMINI_API_KEY не найден в Secrets. Введите его в настройках Streamlit Cloud.")


# ==============================================================================
# 2. ЯДРО (API)
# ==============================================================================
@st.cache_resource
def init_neural_core():
    # Проверяем, не является ли ключ заглушкой перед попыткой настройки API
    if MY_API_KEY == "PLACEHOLDER_KEY_REQUIRED_FOR_CLOUD_DEPLOYMENT":
        return False, "API Key Not Found", None

    try:
        genai.configure(api_key=MY_API_KEY)
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


        /* --- ГЛАВНЫЕ КНОПКИ (ОБЫЧНЫЕ, БЕЗ АНИМАЦИИ) --- */
        .main .stButton button {
            background-color: #1a1a1a !important; 
            border: 2px solid #333 !important; 
            color: #FFFFFF !important; 
            border-radius: 15px !important;
            padding: 15px 5px !important;
            font-weight: 900 !important;
            text-transform: uppercase !important;
            font-size: 16px !important;
            box-shadow: none !important; /* УБРАН ТЕНЬ */
            transition: all 0.1s ease-in-out !important;
            transform: none !important; /* УБРАНО SCALE */
        }

        /* Стиль первой кнопки (как на скриншоте) */
        .main .stButton:nth-child(1) button {
             background-color: #1a1a1a !important; 
             color: #FFFFFF !important; 
             border: 2px solid #444 !important;
        }

        /* Стиль остальных кнопок */
        .main .stButton:not(:nth-child(1)) button {
            background-color: rgba(255, 255, 255, 0.05) !important; 
            border: 2px solid #333 !important;
            color: #FFFFFF !important; 
        }

        /* При наведении */
        .main .stButton button:hover {
            background-color: #00E5FF !important; 
            color: #000000 !important;
            border-color: #00E5FF !important;
        }

        /* При нажатии */
        .main .stButton button:active {
            background-color: #0099CC !important;
            color: #fff !important;
            border-color: #0099CC !important;
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
# 4. ДАННЫЕ (БАЗА И СПИСКИ) - БЕЗ ИЗМЕНЕНИЙ
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

# --- ОГРОМНЫЕ СПИСКИ ДЛЯ РАНДОМА - БЕЗ ИЗМЕНЕНИЙ
RANDOM_RECIPES = [
    "Предложи рецепт редкого французского десерта.",
    "Дай рецепт десерта из японской кухни.",
    "Как приготовить идеальный итальянский Тирамису?",
    "Рецепт современного муссового торта с зеркальной глазурью.",
    "Быстрый рецепт десерта за 15 минут.",
    "Рецепт безглютенового шоколадного фондана.",
    "Что-то необычное из молекулярной кухни для дома.",
    "Рецепт классического австрийского штруделя.",
    "Рецепт португальского Паштел-де-ната.",
    "Как сделать настоящий турецкий рахат-лукум?",
    "Рецепт испанского чуррос с шоколадом.",
    "Секретный рецепт бабушкиного пирога с яблоками.",
    "Рецепт торта 'Красный бархат' в оригинале.",
    "Десерт Павлова: как сделать идеально белым?",
    "Рецепт профитролей с кракелюром.",
    "Как сделать домашнее мороженое без мороженицы?",
    "Рецепт фисташкового рулета с малиной.",
    "Баскский чизкейк (Сан-Себастьян) - рецепт.",
    "Рецепт английского трайфла с ягодами.",
    "Десерт 'Плавающий остров' (Ile Flottante)."
]

RANDOM_FACTS = [
    "Расскажи неочевидный факт из истории шоколада.",
    "Почему сахарная вата такая пушистая? Факт.",
    "Самый дорогой десерт в мире? Факт.",
    "Как появилось мороженое? Краткий факт.",
    "В какой стране едят больше всего сладкого?",
    "Химический факт: почему карамель коричневая?",
    "Откуда пошло название торта 'Наполеон'?",
    "Правда ли, что белый шоколад - это не шоколад?",
    "Какой десерт был любимым у Марии Антуанетты?",
    "История появления круассана (это не Франция!).",
    "Почему марципан так называется?",
    "Сколько слоев должно быть в идеальном Мильфее?",
    "Факт про самое большое печенье в мире.",
    "Почему пончики имеют дырку посередине?",
    "Какой десерт подают на Нобелевском банкете?",
    "История тирамису: правда или миф про публичные дома?",
    "Почему ваниль такая дорогая?",
    "Факт про шоколадную фабрику Вилли Вонки (реальную).",
    "Что такое 'золотой' шоколад?",
    "Как придумали чупа-чупс?"
]

RANDOM_PAIRINGS = [
    "С чем идеально сочетается малина в десертах?",
    "Лучшие компаньоны для темного шоколада.",
    "Необычные сочетания с соленой карамелью.",
    "Что добавить к ванили, чтобы раскрыть вкус?",
    "Сочетание базилика и клубники - почему это работает?",
    "Специи для яблочного пирога, кроме корицы.",
    "С чем сочетать манго в муссовых тортах?",
    "Кофе и десерты: правила идеальной пары.",
    "С чем подавать голубой сыр в десертах?",
    "Неожиданные пары: шоколад и бекон?",
    "С чем сочетается лаванда в выпечке?",
    "Лучшие орехи для морковного торта.",
    "Алкоголь в десертах: что к чему подходит?",
    "Сочетание мяты и шоколада: за и против.",
    "С чем сочетать кокос, кроме ананаса?",
    "Идеальная пара для груши (кроме сыра).",
    "С чем сочетается матча?",
    "Фисташка и малина: почему это классика?",
    "Чем оттенить вкус белого шоколада?",
    "Сочетание розмарина и апельсина."
]

RANDOM_TIPS = [
    "Секрет идеальной меренги, чтобы она не опала.",
    "Как темперировать шоколад в домашних условиях?",
    "Почему бисквит оседает? Совет шефа.",
    "Как сделать песочное тесто рассыпчатым?",
    "Лайфхак для взбивания сливок.",
    "Как спасти перевзбитый ганаш?",
    "Как сделать зеркальную глазурь без пузырей?",
    "Секрет сочных кексов: что добавить?",
    "Как правильно растопить шоколад, чтобы не свернулся?",
    "Почему нельзя открывать духовку при выпечке бисквита?",
    "Как сделать карамель, которая не кристаллизуется?",
    "Совет по работе с желатином и агаром.",
    "Как сделать идеально ровный торт?",
    "Секрет хрустящей корочки у эклеров.",
    "Как быстро размягчить сливочное масло?",
    "Как проверить готовность выпечки без зубочистки?",
    "Совет по окрашиванию крема в яркие цвета.",
    "Как хранить макаронс, чтобы они стали вкуснее?",
    "Что делать, если крем расслоился?",
    "Как аккуратно нарезать торт?"
]

# --- СПИСОК РУГАТЕЛЬСТВ ДЛЯ ЗЛОГО ШЕФА ---
CHEF_INSULTS = [
    "СЛУШАЙ МЕНЯ СЮДА, ИУДА! ",
    "ТЫ ВООБЩЕ КТО ТАКОЙ, ОГУЗОК?! ",
    "ОДНОКЛЕТОЧНЫЙ, КОТОРЫЙ РЕШИЛ СТАТЬ КОНДИТЕРОМ. ",
    "ТЫ ИНФУЗОРИЯ, КОТОРАЯ ДУМАЕТ, ЧТО ОНА УМЕЕТ ГОТОВИТЬ?! ",
    "НЕДОДЕЛАННОЕ ТЕСТО, ГОВОРИ СО МНОЙ! ",
    "ГДЕ ТВОИ РУКИ, ТЫ НИЧТОЖЕСТВО?! ",
    "ТЫ ПРИГОТОВИШЬ ЭТО, ИЛИ Я ТЕБЯ СОТРУ В МУКУ?! ",
    "ПРОКЛЯТЫЙ АМАЛЬГАМ! ",
    "ТЫ ПОЗОР КОНДИТЕРИИ, ТЕБЕ ПОНЯТНО?! "
]


def ai_engine(history, prompt, mode):
    if not STATUS: return "⚠ Ошибка связи с ядром."
    try:
        # !!! ОБНОВЛЕННЫЙ ПРОМПТ ДЛЯ ЗЛОГО ШЕФА (на ты, с ругательствами) !!!
        if mode == "CHEF":
            # Выбираем случайное ругательство для каждого ответа
            random_insult = random.choice(CHEF_INSULTS)
            sys_prompt = f"ТЫ ЗЛОЙ ШЕФ-КОНДИТЕР. Твой тон ГРУБЫЙ, ТЫ говоришь с пользователем НА ТЫ, и постоянно ругаешься. ВСЕГДА НАЧИНАЙ свой ответ с одного из ругательств (например: **{random_insult}**). Твои ответы должны быть профессиональными по сути, но максимально сердитыми, требовательными и наполненными драматизмом. Дай рецепт с граммами, используя **умеренное количество эмодзи** (только самые необходимые: 🔪🔥😩)."
        else:
            sys_prompt = "ТЫ VLADЫКА AI. Умный помощник по десертам. Будь краток и информативен."

        chat = MODEL.start_chat(history=[{"role": "user", "parts": [sys_prompt]}])
        for m in history[-6:]:
            role = "user" if m["role"] == "user" else "model"
            chat.history.append({"role": role, "parts": [m["content"]]})
        return chat.send_message(prompt).text
    except Exception as e:
        return f"⚠ Error: {e}"


# ==============================================================================
# 5. ИНТЕРФЕЙС
# ==============================================================================
if 'history' not in st.session_state: st.session_state.history = []
if 'mode' not in st.session_state: st.session_state.mode = "AI"
if 'vec' not in st.session_state: st.session_state.vec = [5] * len(FEATURES)
if 'trigger_query' not in st.session_state: st.session_state.trigger_query = None


# Функция для принудительного скролла
def scroll_to_end(delay=100):
    components.html(f"""
        <script>
            // Исправленный JS синтаксис для плавного скролла
            setTimeout(() => {{
                const endChatElement = window.parent.document.getElementById('end-chat');
                if (endChatElement) {{
                    endChatElement.scrollIntoView({{behavior: "smooth", block: "end"}});
                }}
            }}, {delay}); 
        </script>
        """, height=0)


# !!! КНОПКА ВХОДА (ПЕРЕД САЙДБАРОМ/ТАБАМИ) !!!
st.markdown("""
<div class="login-button">
    <button onclick="window.parent.alert('Функционал входа через Google пока не реализован!')">
        <span class="google-icon">G</span> Войти
    </button>
</div>
""", unsafe_allow_html=True)

# САЙДБАР
with st.sidebar:
    st.title("⚙️ МЕНЮ")

    st.write("### РЕЖИМ")
    # Обработка сброса history при смене режима
    current_mode = st.session_state.mode
    m = st.radio("", ["Ассистент", "Шеф-Повар"], label_visibility="collapsed")
    new_mode = "CHEF" if m == "Шеф-Повар" else "AI"
    # Сброс истории только при фактической смене режима
    if current_mode != new_mode:
        st.session_state.history = []
    st.session_state.mode = new_mode

    st.write("### ИСТОРИЯ")
    if st.button("🗑 ОЧИСТИТЬ ЧАТ"):
        st.session_state.history = []
        st.rerun()

# --- ТАБЫ ---
t1, t2, t3 = st.tabs(["💬 ЧАТ", "🎛 ВКУСЫ", "📂 БАЗА"])

# --- ЧАТ ---
with t1:
    st.markdown(
        "<h1 style='text-align: center; margin-bottom: 30px;'>Vladыка <span style='color:#00E5FF'>AI</span></h1>",
        unsafe_allow_html=True)

    # Кнопки
    c1, c2, c3, c4 = st.columns(4)


    def set_query(q):
        # Добавляем вопрос пользователя в историю и запускаем перерисовку
        st.session_state.history.append({"role": "user", "content": q})
        st.session_state.trigger_rerun = True

        # Здесь используем списки с рандомом!


    c1.button("🎲 СЛУЧАЙНЫЙ ФАКТ", on_click=set_query, args=(random.choice(RANDOM_FACTS),))
    c2.button("📜 РАНДОМ РЕЦЕПТ", on_click=set_query, args=(random.choice(RANDOM_RECIPES),))
    c3.button("🍷 СОЧЕТАНИЯ", on_click=set_query, args=(random.choice(RANDOM_PAIRINGS),))
    c4.button("💡 СОВЕТ", on_click=set_query, args=(random.choice(RANDOM_TIPS),))

    if 'trigger_rerun' in st.session_state and st.session_state.trigger_rerun:
        st.session_state.trigger_rerun = False
        # Скролл вызывается здесь, перед rerunning, чтобы страница обновилась уже внизу
        scroll_to_end(delay=10)
        st.rerun()

    st.write("")

    # Чат
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Элемент для скроллинга
    st.markdown("<div id='end-chat'></div>", unsafe_allow_html=True)

    # Логика обработки
    prompt = None

    if input_val := st.chat_input("Введите сообщение..."):
        prompt = input_val
        st.session_state.history.append({"role": "user", "content": prompt})
        st.rerun()

    if st.session_state.history and st.session_state.history[-1]["role"] == "user":
        # Скроллим сразу, чтобы увидеть свой вопрос и ожидание
        scroll_to_end(delay=10)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("""<div class="thinking-pulse">⚡ ГЕНЕРАЦИЯ ОТВЕТА...</div>""", unsafe_allow_html=True)

            last_user_msg = st.session_state.history[-1]["content"]

            # Определяем режим
            current_mode = st.session_state.mode

            # Генерируем ответ
            resp = ai_engine(st.session_state.history[:-1], last_user_msg, current_mode)
            placeholder.empty()
            st.markdown(resp)

        st.session_state.history.append({"role": "assistant", "content": resp})

        # Скроллим после добавления ответа
        scroll_to_end(delay=300)

    # --- ВЕКТОРЫ (ОСТАВЛЕНО БЕЗ ИЗМЕНЕНИЙ) ---
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

# --- БАЗА (ОСТАВЛЕНО БЕЗ ИЗМЕНЕНИЙ) ---
with t3:
    st.header("📂 БАЗА ДАННЫХ")
    df = pd.DataFrame(DB)
    sc = pd.DataFrame(df['scores'].tolist(), columns=FEATURES)

    st.dataframe(pd.concat([df[['name', 'desc']], sc], axis=1), use_container_width=True)

