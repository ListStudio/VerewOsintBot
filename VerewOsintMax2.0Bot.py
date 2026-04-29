#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import os
import time
import re
import json
import requests
import random
import socket
import hashlib
import whois
import dns.resolver
import phonenumbers
from phonenumbers import carrier, geocoder, timezone as phone_tz, number_type
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

# ==================== ТВОИ API КЛЮЧИ ====================
PHONE_API_KEY = "162150ebba5cf2754b6ad03d693ac9a4"
PHONE_API_URL = "http://apilayer.net/api/validate"

SHODAN_API_KEY = "JyADHBPN3Tu3HnozydrvkDKxeQmJzuIx"
VT_API_KEY = "7b6efcf6278dd0d7f5e970c2b56142e27eeb34badfd8619a0495f5921ffb1589"
IPINFO_API_KEY = "555049e3bede23"

VK_ACCESS_TOKEN = "vk1.a.y_wbWcVdSOlQWrMEVK6VXZ89yF_3wbwueZR7RWxbU8jCpt6ARMT1uIK0lFFEpGLqqPeDZl8duZ33JHh4VboQw0RX86R4BvETeleDvahwpiCSn3fSukwm8EiPj8ltrwpesylyDOafEzb3MLRXFPNwUul_qzoOWXEsCdIYKwYIosuNyU7dAe6NK1wDO5tjYcBlASXQhS398dTMZB3w3A8VDQ"

TELEGRAM_BOT_TOKEN = "8756195239:AAHfktVDf1P6duaJVV2T4GOYbZE6YmM8GKM"
# =====================================================

def install_libraries():
    libs = ['phonenumbers', 'whois', 'dnspython', 'shodan', 'ipinfo', 'vt-py', 'vk-api', 'python-telegram-bot']
    for lib in libs:
        try:
            if lib == 'dnspython':
                __import__('dns.resolver')
            elif lib == 'vt-py':
                __import__('vt')
            elif lib == 'vk-api':
                __import__('vk_api')
            elif lib == 'python-telegram-bot':
                __import__('telegram')
                __import__('telegram.ext')
            else:
                __import__(lib)
        except ImportError:
            pip_name = 'dnspython' if lib == 'dnspython' else lib
            if lib == 'python-telegram-bot':
                pip_name = 'python-telegram-bot'
            print(f"[*] Установка {pip_name}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "-q"])

install_libraries()

import shodan
import ipinfo
import vt
import vk_api
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Инициализация API
SHODAN_AVAILABLE = True
IPINFO_AVAILABLE = True
ipinfo_handler = ipinfo.getHandler(IPINFO_API_KEY)
VT_AVAILABLE = True
VK_AVAILABLE = True

def normalize_phone(phone):
    phone = re.sub(r'[^\d+]', '', phone)
    if phone.startswith('8') and len(phone) == 11:
        phone = '+7' + phone[1:]
    if phone.startswith('7') and len(phone) == 11:
        phone = '+' + phone
    if not phone.startswith('+'):
        phone = '+' + phone
    return phone

def transliterate(text):
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya', ' ': '', '-': ''
    }
    return ''.join(translit_map.get(c, c) for c in text.lower())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🤖 *Verew Osint Bot*

Привет! Я бот для OSINT разведки.

📌 *Доступные команды:*

`/vk <id или username>` - Поиск профиля ВКонтакте
`/phone <номер>` - Анализ номера телефона
`/ip <ip>` - Информация по IP адресу
`/email <email>` - Анализ email
`/name <ФИО>` - Поиск по ФИО
`/help` - Помощь

📌 *Примеры:*
/vk 1
/vk durov
/phone 89001234567
/ip 8.8.8.8
/email test@gmail.com
/name Иван Иванов

✅ Все API ключи активны
    """
    await update.message.reply_text(text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
📖 *Справка:*

`/vk <id или ник>` - Полный разбор VK профиля
`/phone <номер>` - Анализ номера телефона
`/ip <ip>` - Информация по IP
`/email <email>` - Анализ email
`/name <ФИО>` - Поиск по ФИО
    """
    await update.message.reply_text(text, parse_mode='Markdown')

async def vk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Укажите ID или username\nПример: /vk 1  или  /vk durov")
        return
    
    target = context.args[0]
    await update.message.reply_text(f"🔍 Поиск VK профиля: {target}...")
    
    try:
        vk_session = vk_api.VkApi(token=VK_ACCESS_TOKEN)
        vk = vk_session.get_api()
        
        users = vk.users.get(
            user_ids=target,
            fields='sex,bdate,city,country,status,education,career,contacts,site,counters,online,last_seen,domain'
        )
        
        if not users:
            await update.message.reply_text(f"❌ Пользователь {target} не найден")
            return
        
        user = users[0]
        
        result = f"📌 *VK ПРОФИЛЬ*\n\n"
        result += f"👤 *ID:* {user.get('id', '?')}\n"
        result += f"📛 *Имя:* {user.get('first_name', '?')} {user.get('last_name', '?')}\n"
        
        sex = {0: "Не указан", 1: "Женский", 2: "Мужской"}.get(user.get('sex', 0), "?")
        result += f"🚻 *Пол:* {sex}\n"
        
        if user.get('bdate'):
            result += f"🎂 *Дата рождения:* {user['bdate']}\n"
        if user.get('city'):
            result += f"🏙️ *Город:* {user['city'].get('title', '?')}\n"
        if user.get('country'):
            result += f"🌍 *Страна:* {user['country'].get('title', '?')}\n"
        
        if user.get('domain'):
            result += f"🔗 *Ссылка:* https://vk.com/{user['domain']}\n"
        
        if user.get('contacts'):
            if user['contacts'].get('mobile_phone'):
                result += f"📱 *Телефон:* {user['contacts']['mobile_phone']}\n"
        if user.get('site'):
            result += f"🌐 *Сайт:* {user['site']}\n"
        
        if user.get('education'):
            edu = user['education']
            if edu.get('university_name'):
                result += f"🎓 *ВУЗ:* {edu['university_name']}\n"
        
        if user.get('status'):
            result += f"📝 *Статус:* {user['status'][:100]}\n"
        
        counters = user.get('counters', {})
        if counters:
            result += f"\n📊 *СТАТИСТИКА:*\n"
            result += f"👥 Друзей: {counters.get('friends', 0)}\n"
            result += f"📸 Подписчиков: {counters.get('followers', 0)}\n"
        
        if user.get('online'):
            result += f"\n🟢 *Онлайн:* Да"
        else:
            last_seen = user.get('last_seen', {})
            if last_seen.get('time'):
                lt = datetime.fromtimestamp(last_seen['time'])
                result += f"\n🔴 *Был в сети:* {lt.strftime('%Y-%m-%d %H:%M:%S')}"
        
        await update.message.reply_text(result, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def phone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Укажите номер телефона\nПример: /phone 89001234567")
        return
    
    phone = normalize_phone(context.args[0])
    await update.message.reply_text(f"📞 Анализ номера: {phone}...")
    
    result = f"📞 *РЕЗУЛЬТАТЫ АНАЛИЗА*\n\n"
    
    try:
        parsed = phonenumbers.parse(phone, None)
        result += f"📱 *Формат:* {phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)}\n"
        result += f"🏷️ *Код страны:* +{parsed.country_code}\n"
        
        country = geocoder.description_for_number(parsed, "ru")
        oper = carrier.name_for_number(parsed, "ru")
        if country:
            result += f"🌍 *Страна:* {country}\n"
        if oper:
            result += f"📡 *Оператор:* {oper}\n"
        
        is_valid = "✅ Да" if phonenumbers.is_valid_number(parsed) else "❌ Нет"
        result += f"✓ *Валидный:* {is_valid}\n"
        
        await update.message.reply_text(result, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    # Дополнительный поиск
    phone_clean = phone.replace('+', '')
    search_text = f"\n🔍 *Поиск по номеру:*\n"
    search_text += f"🔗 VK: https://vk.com/search?c[phone]={phone_clean}\n"
    search_text += f"🔗 Google: https://www.google.com/search?q=%22{phone}%22"
    await update.message.reply_text(search_text, parse_mode='Markdown')

async def ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Укажите IP адрес\nПример: /ip 8.8.8.8")
        return
    
    ip = context.args[0]
    await update.message.reply_text(f"🖥️ Анализ IP: {ip}...")
    
    result = f"🖥️ *ИНФОРМАЦИЯ ПО IP*\n\n"
    
    try:
        details = ipinfo_handler.getDetails(ip)
        result += f"🌍 *Страна:* {details.country if details.country else '?'}\n"
        result += f"🏙️ *Город:* {details.city if details.city else '?'}\n"
        result += f"🗺️ *Регион:* {details.region if details.region else '?'}\n"
        result += f"🏢 *Организация:* {details.org if details.org else '?'}\n"
        if details.loc:
            result += f"📍 *Координаты:* {details.loc}\n"
            result += f"🗺️ *Карта:* https://www.google.com/maps?q={details.loc}\n"
        
        await update.message.reply_text(result, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    # Shodan ссылка
    if SHODAN_AVAILABLE:
        shodan_text = f"\n🔗 *Shodan:* https://www.shodan.io/host/{ip}"
        await update.message.reply_text(shodan_text, parse_mode='Markdown')

async def email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Укажите email\nПример: /email test@gmail.com")
        return
    
    email = context.args[0]
    await update.message.reply_text(f"📧 Анализ email: {email}...")
    
    if '@' not in email:
        await update.message.reply_text("❌ Неверный формат email")
        return
    
    username = email.split('@')[0]
    domain = email.split('@')[1]
    
    result = f"📧 *ИНФОРМАЦИЯ ПО EMAIL*\n\n"
    result += f"👤 *Username:* {username}\n"
    result += f"🌐 *Домен:* {domain}\n\n"
    
    email_hash = hashlib.md5(email.lower().encode()).hexdigest()
    result += f"🖼️ *Gravatar:* https://www.gravatar.com/{email_hash}\n\n"
    
    result += f"🔍 *Поиск:*\n"
    result += f"🔗 Google: https://www.google.com/search?q=%22{email}%22\n"
    result += f"🔗 Dehashed: https://dehashed.com/search?query={email}\n"
    result += f"🔗 LeakCheck: https://leakcheck.net/search?q={email}\n"
    result += f"🔗 VK поиск: https://vk.com/search?c[email]={email}"
    
    await update.message.reply_text(result, parse_mode='Markdown')

async def name_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Укажите ФИО\nПример: /name Иван Иванов")
        return
    
    fullname = ' '.join(context.args)
    await update.message.reply_text(f"👤 Поиск по ФИО: {fullname}...")
    
    name_parts = fullname.strip().split()
    if len(name_parts) < 2:
        await update.message.reply_text("❌ Введите имя и фамилию")
        return
    
    first_name = name_parts[0]
    last_name = name_parts[1]
    
    first_en = transliterate(first_name)
    last_en = transliterate(last_name)
    
    result = f"👤 *РЕЗУЛЬТАТЫ ПОИСКА*\n\n"
    result += f"📛 *Имя:* {first_name}\n"
    result += f"📛 *Фамилия:* {last_name}\n"
    result += f"🔤 *Имя (EN):* {first_en}\n"
    result += f"🔤 *Фамилия (EN):* {last_en}\n\n"
    
    result += f"🔍 *Проверка в VK:*\n"
    result += f"🔗 https://vk.com/{first_en}{last_en}\n"
    result += f"🔗 https://vk.com/{first_en}.{last_en}\n"
    result += f"🔗 https://vk.com/{first_en}_{last_en}\n\n"
    
    result += f"🔍 *Поисковые ссылки:*\n"
    result += f"🔗 Google: https://www.google.com/search?q={fullname.replace(' ', '+')}\n"
    result += f"🔗 VK: https://vk.com/search?c[name]={fullname.replace(' ', '+')}\n"
    result += f"🔗 Яндекс: https://yandex.ru/search/?text={fullname}"
    
    await update.message.reply_text(result, parse_mode='Markdown')

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Неизвестная команда. Введите /help для списка команд")

def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                    Verew Osint Telegram Bot                      ║
║                    Запуск бота...                                 ║
║                    Автор: @Verew1                                ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("vk", vk_command))
    app.add_handler(CommandHandler("phone", phone_command))
    app.add_handler(CommandHandler("ip", ip_command))
    app.add_handler(CommandHandler("email", email_command))
    app.add_handler(CommandHandler("name", name_command))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))
    
    print("✅ Бот запущен! Найди его в Telegram: @VerewOsintBot")
    print("📌 Команды: /vk, /phone, /ip, /email, /name")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
