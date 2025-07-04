import os
import requests
import datetime
import logging
from cachetools import TTLCache
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "YOUR_TELEGRAMM_BOT_TOKEN"
DEVELOPER = "@MaloyBegonia"
CACHE_TTL = 600
REQUEST_TIMEOUT = 15

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

cache = TTLCache(maxsize=100, ttl=CACHE_TTL)

CRYPTO_SYMBOLS = {
    'BTC': '₿ Bitcoin', 'ETH': 'Ξ Ethereum', 'BNB': '🔶 Binance Coin',
    'XRP': '✕ Ripple', 'SOL': '🔹 Solana', 'ADA': '🅰 Cardano',
    'DOGE': '🐕 Dogecoin', 'DOT': '● Polkadot', 'SHIB': '🐕 Shiba Inu'
}

FIAT_SYMBOLS = {
    'USD': '💵 Доллар', 'EUR': '💶 Евро', 'GBP': '💷 Фунт',
    'CNY': '🇨🇳 Юань', 'JPY': '🇯🇵 Иена', 'UAH': '🇺🇦 Гривна'
}

class RateFetcher:
    @staticmethod
    async def fetch_rates():
        if 'rates' in cache:
            return cache['rates']

        try:
            cbr_data = await RateFetcher._fetch_cbr_rates()
            crypto_data = await RateFetcher._fetch_crypto_rates()
            uah_rate = await RateFetcher._fetch_uah_rate()

            rates = {
                'date': datetime.datetime.now().strftime('%d.%m.%Y %H:%M'),
                'fiat': cbr_data,
                'crypto': crypto_data
            }
            rates['fiat']['UAH'] = uah_rate

            cache['rates'] = rates
            return rates
        except Exception as e:
            logger.error(f"Ошибка получения курсов: {e}")
            return None

    @staticmethod
    async def _fetch_cbr_rates():
        response = requests.get(
            'https://www.cbr-xml-daily.ru/daily_json.js',
            timeout=REQUEST_TIMEOUT
        )
        data = response.json()
        return {
            'USD': data['Valute']['USD']['Value'],
            'EUR': data['Valute']['EUR']['Value'],
            'GBP': data['Valute']['GBP']['Value'],
            'CNY': data['Valute']['CNY']['Value'],
            'JPY': data['Valute']['JPY']['Value'] / 100
        }

    @staticmethod
    async def _fetch_crypto_rates():
        crypto_ids = ['bitcoin', 'ethereum', 'binancecoin', 'ripple',
                    'solana', 'cardano', 'dogecoin', 'polkadot', 'shiba-inu']
        response = requests.get(
            'https://api.coingecko.com/api/v3/simple/price',
            params={
                'ids': ','.join(crypto_ids),
                'vs_currencies': 'usd,rub'
            },
            timeout=REQUEST_TIMEOUT
        )
        data = response.json()
        return {
            'BTC': data['bitcoin']['usd'],
            'ETH': data['ethereum']['usd'],
            'BNB': data['binancecoin']['usd'],
            'XRP': data['ripple']['usd'],
            'SOL': data['solana']['usd'],
            'ADA': data['cardano']['usd'],
            'DOGE': data['dogecoin']['usd'],
            'DOT': data['polkadot']['usd'],
            'SHIB': data['shiba-inu']['usd']
        }

    @staticmethod
    async def _fetch_uah_rate():
        try:
            response = requests.get(
                'https://api.privatbank.ua/p24api/pubinfo?json&exchange&coursid=5',
                timeout=REQUEST_TIMEOUT
            )
            return float(response.json()[0]['sale'])
        except:
            return 36.5

def get_keyboard():
    return {
        'start': ReplyKeyboardMarkup([[KeyboardButton("🚀 Старт")]], resize_keyboard=True),
        'main': ReplyKeyboardMarkup([
            ["💵 USD", "💶 EUR", "💷 GBP"],
            ["🇨🇳 CNY", "🇯🇵 JPY", "🇺🇦 UAH"],
            ["₿ Криптовалюты", "📊 Все курсы"],
            ["🔄 Обновить", "ℹ️ Помощь"]
        ], resize_keyboard=True),
        'crypto': ReplyKeyboardMarkup([
            ["₿ BTC", "Ξ ETH", "🔶 BNB"],
            ["✕ XRP", "🔹 SOL", "🅰 ADA"],
            ["🐕 DOGE", "● DOT", "🐕 SHIB"],
            ["🔙 Назад"]
        ], resize_keyboard=True)
    }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboards = get_keyboard()
    await update.message.reply_text(
        f"Привет! Я бот для отслеживания курсов валют и криптовалют.\n"
        f"Разработчик: {DEVELOPER}\n\n"
        "Нажмите '🚀 Старт' чтобы начать!",
        reply_markup=keyboards['start']
    )

async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Доступные команды:\n"
        "- Выберите валюту для просмотра курса\n"
        "- '📊 Все курсы' - показать все курсы\n"
        "- '🔄 Обновить' - обновить данные\n"
        "- 'ℹ️ Помощь' - это сообщение"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    keyboards = get_keyboard()

    if text == "🚀 Старт":
        await update.message.reply_text("Выберите действие:", reply_markup=keyboards['main'])
    elif text == "₿ Криптовалюты":
        await update.message.reply_text("Выберите криптовалюту:", reply_markup=keyboards['crypto'])
    elif text == "🔙 Назад":
        await update.message.reply_text("Главное меню:", reply_markup=keyboards['main'])
    elif text == "📊 Все курсы":
        await show_all_rates(update, context)
    elif text == "🔄 Обновить":
        await refresh_rates(update, context)
    elif text == "ℹ️ Помощь":
        await handle_help(update, context)
    elif text in ["🇨🇳 CNY", "🇯🇵 JPY", "🇺🇦 UAH"]: 
        currency = text.split()[-1] 
        await show_rate(update, context, currency)
    elif len(text) > 2 and text[2:] in {**FIAT_SYMBOLS, **CRYPTO_SYMBOLS}:
        await show_rate(update, context, text[2:])
    else:
        await update.message.reply_text("Неизвестная команда")

async def show_rate(update: Update, context: ContextTypes.DEFAULT_TYPE, currency: str):
    rates = await RateFetcher.fetch_rates()
    if not rates:
        await update.message.reply_text("Не удалось получить данные. Попробуйте позже.")
        return

    try:
        if currency in rates['fiat']:
            symbol = FIAT_SYMBOLS.get(currency, '')
            await update.message.reply_text(
                f"{symbol}\nКурс: {rates['fiat'][currency]:.2f} RUB\n"
                f"Обновлено: {rates['date']}"
            )
        elif currency in rates['crypto']:
            symbol = CRYPTO_SYMBOLS.get(currency, '')
            usd_rate = rates['fiat']['USD']
            await update.message.reply_text(
                f"{symbol}\nЦена: ${rates['crypto'][currency]:,.4f}\n"
                f"В рублях: {rates['crypto'][currency] * usd_rate:,.2f} RUB\n"
                f"Обновлено: {rates['date']}"
            )
    except Exception as e:
        logger.error(f"Ошибка отображения курса: {e}")
        await update.message.reply_text("Ошибка отображения данных")

async def show_all_rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rates = await RateFetcher.fetch_rates()
    if not rates:
        await update.message.reply_text("Не удалось получить данные.")
        return

    message = [f"Курсы на {rates['date']}\n\nФиатные валюты:"]
    for curr, rate in rates['fiat'].items():
        symbol = FIAT_SYMBOLS.get(curr, '')
        message.append(f"{symbol}: {rate:.2f} RUB")

    message.append("\nКриптовалюты:")
    for curr, price in rates['crypto'].items():
        symbol = CRYPTO_SYMBOLS.get(curr, '')
        message.append(f"{symbol}: ${price:,.4f}")

    await update.message.reply_text("\n".join(message))

async def refresh_rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'rates' in cache:
        del cache['rates']
    await update.message.reply_text("Данные обновляются...")
    await show_all_rates(update, context)

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", handle_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    try:
        app.run_polling()
    except Exception as e:
        logger.critical(f"Ошибка в работе бота: {e}")
    finally:
        logger.info("Бот остановлен")

if __name__ == '__main__':
    main()
