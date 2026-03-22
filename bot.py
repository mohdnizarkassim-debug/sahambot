"""
SahamBot MY — Telegram Bot Analisa Saham Bursa Malaysia
Pilot Project v2.2 — Privacy + Save Feature
"""

import logging
import csv
import io
import math
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.helpers import escape_markdown
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler,
    filters, ContextTypes
)

from database import init_db, get_user, create_user, increment_usage, log_pilot
from analisa import analisa_engine, CANDLE_INFO

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

(
    STATE_MAIN,
    STATE_TICKER,
    STATE_TIMEFRAME,
    STATE_CANDLE_COUNT,
    STATE_CANDLE_CONFIRM,
    STATE_INPUT_METHOD,
    STATE_GUIDED_CANDLE,
    STATE_WAITING_CSV,
    STATE_SAVE,
) = range(9)

MAX_CSV_SIZE_BYTES = 1024 * 1024
TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{1,11}$")

def md(text: str) -> str:
    return escape_markdown(str(text), version=1)

def is_valid_ticker(ticker: str) -> bool:
    return bool(TICKER_PATTERN.fullmatch(ticker))

def parse_candle_values(raw_values):
    if len(raw_values) != 5:
        raise ValueError("format")

    values = []
    for raw in raw_values:
        cleaned = str(raw).replace(',', '').strip()
        if not cleaned:
            raise ValueError("format")
        value = float(cleaned)
        if not math.isfinite(value):
            raise ValueError("format")
        values.append(value)

    o, h, l, c, v = values
    if min(o, h, l, c) <= 0 or v < 0:
        raise ValueError("range")
    if h < max(o, c) or l > min(o, c) or h < l:
        raise ValueError("logic")
    return o, h, l, c, v

async def send_analysis_result(message, context, user_id: int, candles, ticker: str, tf: str, tier: int, count: int, input_method: str):
    tf_label = {"D":"Daily","W":"Weekly","M":"Monthly","Y":"Yearly"}
    safe_ticker = md(ticker)

    await message.reply_text(
        f"✅ *Semua {count} candle diterima!*\n\n⏳ Menganalisa *{safe_ticker}*...",
        parse_mode='Markdown'
    )

    result = analisa_engine(candles, ticker, tf, tier)
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    sent_message = await message.reply_text(
        f"{result}\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "⚠️ *NOTIS PENTING*\n"
        f"• 1 token telah ditolak\n"
        f"• Data analisa *TIDAK* tersimpan dalam sistem\n"
        f"• Sila simpan analisa ini sekarang\n"
        f"• Masa: {md(timestamp)}",
        reply_markup=kb_after_analisa(),
        parse_mode='Markdown'
    )

    increment_usage(user_id)
    log_pilot(user_id, tf, count, input_method, tier)

    context.user_data['last_result'] = result
    context.user_data['last_ticker'] = ticker
    context.user_data['last_tf'] = tf_label.get(tf, tf)
    context.user_data['last_count'] = count
    context.user_data['candles_collected'] = []
    context.user_data['current_candle'] = 1

    return sent_message

# ─────────────────────────────────────────
# KEYBOARDS
# ─────────────────────────────────────────
def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Analisa Saham", callback_data="menu_analisa")],
        [InlineKeyboardButton("👤 Status Akaun", callback_data="menu_status")],
        [InlineKeyboardButton("💎 Upgrade Plan", callback_data="menu_upgrade")],
        [InlineKeyboardButton("📖 Panduan", callback_data="menu_help")],
    ])

def kb_dashboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Dashboard", callback_data="menu_main")],
    ])

def kb_during_input():
    """Butang semasa input candle"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Tukar Saham", callback_data="tukar_saham"),
         InlineKeyboardButton("🏠 Dashboard", callback_data="menu_main")],
    ])

def kb_after_analisa():
    """Butang lepas analisa keluar"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📨 Forward ke Saved Messages", callback_data="save_forward")],
        [InlineKeyboardButton("📄 Download .txt", callback_data="save_txt")],
        [InlineKeyboardButton("📊 Analisa Lagi", callback_data="analisa_lagi"),
         InlineKeyboardButton("🔄 Saham Lain", callback_data="saham_lain")],
        [InlineKeyboardButton("🏠 Dashboard", callback_data="menu_main")],
    ])

# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────
async def show_dashboard(target, context, edit=False):
    if hasattr(target, 'from_user'):
        user_id = target.from_user.id
        name = md(target.from_user.first_name)
    else:
        user_id = target.effective_user.id
        name = md(target.effective_user.first_name)

    user = get_user(user_id)
    tier = user[2] if user else 0
    usage = user[3] if user else 0
    tier_label = "👑 PRO" if tier == 2 else "💎 PREMIUM" if tier == 1 else "⚡ FREE"
    limit = "∞" if tier >= 1 else "3"

    msg = (
        f"👋 *Selamat Datang, {name}!*\n\n"
        "🤖 *SahamBot MY*\n"
        "Bot Analisa Teknikal Saham Bursa Malaysia\n\n"
        f"Plan: {tier_label}  |  Analisa hari ini: {usage}/{limit}\n\n"
        "Pilih menu di bawah:"
    )

    if edit:
        await target.edit_message_text(msg, reply_markup=kb_main(), parse_mode='Markdown')
    else:
        await target.message.reply_text(msg, reply_markup=kb_main(), parse_mode='Markdown')

# ─────────────────────────────────────────
# /start
# ─────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user.id, user.username or user.first_name)
    context.user_data.clear()
    await show_dashboard(update, context, edit=False)
    return STATE_MAIN

# ─────────────────────────────────────────
# MAIN MENU
# ─────────────────────────────────────────
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_main":
        await show_dashboard(query, context, edit=True)
        return STATE_MAIN
    elif data == "menu_status":
        return await show_status(query, context)
    elif data == "menu_upgrade":
        return await show_upgrade(query, context)
    elif data == "menu_help":
        return await show_help(query, context)
    elif data == "menu_analisa":
        return await start_analisa(query, context)
    elif data == "analisa_lagi":
        ticker = context.user_data.get('ticker', '')
        context.user_data.clear()
        context.user_data['ticker'] = ticker
        return await start_analisa(query, context, ticker=ticker)
    elif data == "saham_lain":
        context.user_data.clear()
        return await start_analisa(query, context)
    elif data == "tukar_saham":
        # Reset data, balik taip saham — token TAK ditolak
        context.user_data['candles_collected'] = []
        context.user_data['current_candle'] = 1
        context.user_data['ticker'] = ''
        await query.edit_message_text(
            "🔄 *Tukar Saham*\n\nTaip *kod saham* baru:\n\n"
            "Contoh: `MAYBANK` `TENAGA` `PBBANK`\n\n"
            "_(Taip /start untuk Dashboard)_",
            parse_mode='Markdown'
        )
        return STATE_TICKER
    elif data == "save_forward":
        return await handle_save_forward(query, context)
    elif data == "save_txt":
        return await handle_save_txt(query, context)

# ─────────────────────────────────────────
# STATUS
# ─────────────────────────────────────────
async def show_status(query, context):
    user_id = query.from_user.id
    user = get_user(user_id)
    tier = user[2] if user else 0
    usage = user[3] if user else 0
    tier_label = "👑 PRO" if tier == 2 else "💎 PREMIUM" if tier == 1 else "⚡ FREE"
    limit = "∞" if tier >= 1 else "3"
    extra = "\n💡 Upgrade untuk analisa unlimited!" if tier == 0 else \
            "\n💡 Upgrade ke PRO untuk MTF & Risk Management!" if tier == 1 else \
            "\n✅ Kau ada akses penuh semua feature!"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Upgrade Sekarang", callback_data="menu_upgrade")],
        [InlineKeyboardButton("🏠 Dashboard", callback_data="menu_main")],
    ]) if tier < 2 else kb_dashboard()
    await query.edit_message_text(
        f"👤 *Status Akaun*\n\nPlan: {tier_label}\nAnalisa hari ini: {usage}/{limit}\n{extra}",
        reply_markup=keyboard, parse_mode='Markdown'
    )
    return STATE_MAIN

# ─────────────────────────────────────────
# UPGRADE
# ─────────────────────────────────────────
async def show_upgrade(query, context):
    msg = (
        "💎 *Plan SahamBot MY*\n\n"
        "⚡ *FREE* — Percuma\n"
        "• Daily | 5 candle | Guided input\n"
        "• RSI, MA, S&R, Pattern asas\n"
        "• 3 analisa sehari\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "💎 *PREMIUM — RM25/bulan*\n"
        "• Daily + Weekly + Monthly\n"
        "• 5–10 candle bebas pilih\n"
        "• Guided input + CSV upload\n"
        "• MACD, Bollinger Bands, Fibonacci\n"
        "• Analisa unlimited\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "👑 *PRO — RM60/bulan*\n"
        "• Semua Premium +\n"
        "• Yearly timeframe\n"
        "• MTF Confluence Analysis\n"
        "• Risk Management Calculator\n"
        "• Wyckoff + Fair Value Gap\n"
        "• Priority support\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "📲 *Cara Subscribe:*\n"
        "1. Transfer ke: `MAYBANK 1234 5678 9012`\n"
        "2. Screenshot resit → @adminSahamBot\n"
        "3. Aktif dalam 1 jam"
    )
    await query.edit_message_text(msg, reply_markup=kb_dashboard(), parse_mode='Markdown')
    return STATE_MAIN

# ─────────────────────────────────────────
# HELP
# ─────────────────────────────────────────
async def show_help(query, context):
    msg = (
        "📖 *Panduan SahamBot MY*\n\n"
        "*Format OHLCV:*\n"
        "`OPEN HIGH LOW CLOSE VOLUME`\n\n"
        "*Contoh:*\n"
        "`9.20 9.80 9.10 9.50 1250000`\n\n"
        "*Cara input guided:*\n"
        "• Bot tanya satu candle satu masa\n"
        "• Taip satu baris → tekan Send\n"
        "• Progress bar tunjuk kemajuan\n\n"
        "*Data dari mana?*\n"
        "• TradingView, i3investor\n"
        "• Yahoo Finance, Rakuten Trade\n\n"
        "*Tips:*\n"
        "• Susun dari LAMA → BARU\n"
        "• HIGH > OPEN & CLOSE\n"
        "• LOW < OPEN & CLOSE\n\n"
        "*Pasal Token & Data:*\n"
        "• Token ditolak SELEPAS analisa keluar\n"
        "• Tukar saham = token TIDAK ditolak\n"
        "• Data analisa tidak tersimpan — sila save!"
    )
    await query.edit_message_text(msg, reply_markup=kb_dashboard(), parse_mode='Markdown')
    return STATE_MAIN

# ─────────────────────────────────────────
# ANALISA — Step 1: Tanya Nama Saham
# ─────────────────────────────────────────
async def start_analisa(query, context, ticker=''):
    user_id = query.from_user.id
    user = get_user(user_id)
    tier = user[2] if user else 0
    usage = user[3] if user else 0

    if tier == 0 and usage >= 3:
        await query.edit_message_text(
            "⛔ *Had analisa harian habis (3/3).*\n\nUpgrade untuk analisa unlimited!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Upgrade", callback_data="menu_upgrade")],
                [InlineKeyboardButton("🏠 Dashboard", callback_data="menu_main")],
            ]), parse_mode='Markdown'
        )
        return STATE_MAIN

    context.user_data['tier'] = tier

    if ticker:
        context.user_data['ticker'] = ticker
        return await show_timeframe(query, context)

    await query.edit_message_text(
        "📊 *Analisa Saham*\n\nTaip *kod saham*:\n\n"
        "Contoh: `MAYBANK` `TENAGA` `PBBANK`\n\n"
        "_(Taip /start untuk Dashboard)_",
        parse_mode='Markdown'
    )
    return STATE_TICKER

# ─────────────────────────────────────────
# ANALISA — Step 2: Terima Ticker
# ─────────────────────────────────────────
async def handle_ticker_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.strip().upper()

    if len(ticker) < 2 or len(ticker) > 12 or not is_valid_ticker(ticker):
        await update.message.reply_text(
            "❗ Kod saham tak valid.\nContoh: `MAYBANK`, `TENAGA`",
            parse_mode='Markdown'
        )
        return STATE_TICKER

    context.user_data['ticker'] = ticker
    tier = context.user_data.get('tier', 0)

    rows = [[InlineKeyboardButton("📅 Daily", callback_data="tf_D")]]
    if tier >= 1:
        rows += [[InlineKeyboardButton("📆 Weekly", callback_data="tf_W")],
                 [InlineKeyboardButton("🗓️ Monthly", callback_data="tf_M")]]
    if tier >= 2:
        rows += [[InlineKeyboardButton("📊 Yearly", callback_data="tf_Y")],
                 [InlineKeyboardButton("🔥 MTF", callback_data="tf_MTF")]]
    rows.append([InlineKeyboardButton("🔄 Tukar Saham", callback_data="tukar_saham"),
                 InlineKeyboardButton("🏠 Dashboard", callback_data="menu_main")])

    locked = "\n🔒 Weekly/Monthly/Yearly — Premium & Pro" if tier == 0 else \
             "\n🔒 Yearly & MTF — Pro sahaja" if tier == 1 else ""

    await update.message.reply_text(
        f"✅ Saham: *{md(ticker)}*\n\nPilih *Timeframe*:{locked}",
        reply_markup=InlineKeyboardMarkup(rows), parse_mode='Markdown'
    )
    return STATE_TIMEFRAME

# ─────────────────────────────────────────
# Show Timeframe
# ─────────────────────────────────────────
async def show_timeframe(query, context):
    ticker = context.user_data.get('ticker', '')
    tier = context.user_data.get('tier', 0)

    rows = [[InlineKeyboardButton("📅 Daily", callback_data="tf_D")]]
    if tier >= 1:
        rows += [[InlineKeyboardButton("📆 Weekly", callback_data="tf_W")],
                 [InlineKeyboardButton("🗓️ Monthly", callback_data="tf_M")]]
    if tier >= 2:
        rows += [[InlineKeyboardButton("📊 Yearly", callback_data="tf_Y")],
                 [InlineKeyboardButton("🔥 MTF", callback_data="tf_MTF")]]
    rows.append([InlineKeyboardButton("🔄 Tukar Saham", callback_data="tukar_saham"),
                 InlineKeyboardButton("🏠 Dashboard", callback_data="menu_main")])

    locked = "\n🔒 Weekly/Monthly/Yearly — Premium & Pro" if tier == 0 else \
             "\n🔒 Yearly & MTF — Pro sahaja" if tier == 1 else ""

    await query.edit_message_text(
        f"✅ Saham: *{md(ticker)}*\n\nPilih *Timeframe*:{locked}",
        reply_markup=InlineKeyboardMarkup(rows), parse_mode='Markdown'
    )
    return STATE_TIMEFRAME

# ─────────────────────────────────────────
# ANALISA — Step 3: Pilih Candle
# ─────────────────────────────────────────
async def handle_timeframe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tf = query.data.replace("tf_", "")
    context.user_data['timeframe'] = tf
    tier = context.user_data.get('tier', 0)
    ticker = context.user_data.get('ticker', 'SAHAM')
    tf_label = {"D":"Daily","W":"Weekly","M":"Monthly","Y":"Yearly","MTF":"Multi-Timeframe"}

    if tier == 0:
        context.user_data['candle_count'] = 5
        return await show_candle_warning(query, context, 5)

    await query.edit_message_text(
        f"✅ *{md(ticker)}* | *{md(tf_label.get(tf,tf))}*\n\nPilih *Bilangan Candle*:\n_(5 = minimum, 10 = paling tepat)_",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("5",callback_data="c_5"),
             InlineKeyboardButton("6",callback_data="c_6"),
             InlineKeyboardButton("7",callback_data="c_7")],
            [InlineKeyboardButton("8",callback_data="c_8"),
             InlineKeyboardButton("9",callback_data="c_9"),
             InlineKeyboardButton("10",callback_data="c_10")],
            [InlineKeyboardButton("🔄 Tukar Saham",callback_data="tukar_saham"),
             InlineKeyboardButton("🏠 Dashboard",callback_data="menu_main")],
        ]), parse_mode='Markdown'
    )
    return STATE_CANDLE_COUNT

# ─────────────────────────────────────────
# ANALISA — Step 4: Candle Warning
# ─────────────────────────────────────────
async def handle_candle_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    count = int(query.data.replace("c_",""))
    context.user_data['candle_count'] = count
    return await show_candle_warning(query, context, count)

async def show_candle_warning(query, context, count: int):
    info = CANDLE_INFO[count]
    ticker = context.user_data.get('ticker','SAHAM')
    tf = context.user_data.get('timeframe','D')
    tf_label = {"D":"Daily","W":"Weekly","M":"Monthly","Y":"Yearly"}
    available = "\n".join([f"  ✅ {i}" for i in info['available']])
    limited = "\n".join([f"  ⚠️ {i}" for i in info['limited']]) if info['limited'] else "  —"
    unavailable = "\n".join([f"  ❌ {i}" for i in info['unavailable']]) if info['unavailable'] else "  —"
    await query.edit_message_text(
        f"✅ *{md(ticker)}* | {md(tf_label.get(tf,tf))} | {count} Candle\n\n"
        f"*Indicator Tersedia:*\n{available}\n\n"
        f"*Kurang Tepat:*\n{limited}\n\n"
        f"*Tidak Tersedia:*\n{unavailable}\n\n"
        f"💡 {info['suitable']}\n\nTeruskan dengan *{count} candle*?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Teruskan",callback_data="confirm_yes"),
             InlineKeyboardButton("🔄 Tukar",callback_data="confirm_change")],
            [InlineKeyboardButton("🔄 Tukar Saham",callback_data="tukar_saham"),
             InlineKeyboardButton("🏠 Dashboard",callback_data="menu_main")],
        ]), parse_mode='Markdown'
    )
    return STATE_CANDLE_CONFIRM

# ─────────────────────────────────────────
# ANALISA — Step 5: Confirm
# ─────────────────────────────────────────
async def handle_candle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_change":
        await query.edit_message_text(
            "🔄 *Pilih semula bilangan candle:*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("5",callback_data="c_5"),
                 InlineKeyboardButton("6",callback_data="c_6"),
                 InlineKeyboardButton("7",callback_data="c_7")],
                [InlineKeyboardButton("8",callback_data="c_8"),
                 InlineKeyboardButton("9",callback_data="c_9"),
                 InlineKeyboardButton("10",callback_data="c_10")],
                [InlineKeyboardButton("🔄 Tukar Saham",callback_data="tukar_saham"),
                 InlineKeyboardButton("🏠 Dashboard",callback_data="menu_main")],
            ]), parse_mode='Markdown'
        )
        return STATE_CANDLE_COUNT

    tier = context.user_data.get('tier', 0)
    ticker = context.user_data.get('ticker','SAHAM')
    tf = context.user_data.get('timeframe','D')
    count = context.user_data.get('candle_count', 5)
    tf_label = {"D":"Daily","W":"Weekly","M":"Monthly","Y":"Yearly"}

    context.user_data['candles_collected'] = []
    context.user_data['current_candle'] = 1
    context.user_data['input_method'] = 'manual'

    if tier == 0:
        await query.edit_message_text(
            f"⌨️ *Input Data — {md(ticker)} {md(tf_label.get(tf,tf))}*\n\n"
            f"📊 *Candle 1/{count}*\n\n"
            "`OPEN HIGH LOW CLOSE VOLUME`\n\n"
            "📌 Contoh: `9.10 9.45 9.05 9.20 980000`\n\n"
            "💡 _Token hanya ditolak selepas analisa keluar_",
            parse_mode='Markdown'
        )
        return STATE_GUIDED_CANDLE

    await query.edit_message_text(
        f"✅ *{md(ticker)}* | {md(tf_label.get(tf,tf))} | {count} Candle\n\nPilih *Cara Input:*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⌨️ Input Guided",callback_data="input_manual")],
            [InlineKeyboardButton("📎 Upload CSV",callback_data="input_csv")],
            [InlineKeyboardButton("🔄 Tukar Saham",callback_data="tukar_saham"),
             InlineKeyboardButton("🏠 Dashboard",callback_data="menu_main")],
        ]), parse_mode='Markdown'
    )
    return STATE_INPUT_METHOD

# ─────────────────────────────────────────
# Input Method
# ─────────────────────────────────────────
async def handle_input_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.replace("input_","")
    context.user_data['input_method'] = method
    ticker = context.user_data.get('ticker','SAHAM')
    tf = context.user_data.get('timeframe','D')
    count = context.user_data.get('candle_count', 5)
    tf_label = {"D":"Daily","W":"Weekly","M":"Monthly","Y":"Yearly"}

    if method == 'manual':
        context.user_data['candles_collected'] = []
        context.user_data['current_candle'] = 1
        await query.edit_message_text(
            f"⌨️ *Input Data — {md(ticker)} {md(tf_label.get(tf,tf))}*\n\n"
            f"📊 *Candle 1/{count}*\n\n"
            "`OPEN HIGH LOW CLOSE VOLUME`\n\n"
            "📌 Contoh: `9.10 9.45 9.05 9.20 980000`\n\n"
            "💡 _Token hanya ditolak selepas analisa keluar_",
            parse_mode='Markdown'
        )
        return STATE_GUIDED_CANDLE
    else:
        await query.edit_message_text(
            f"📎 *Upload CSV — {md(ticker)}*\n\n"
            "Hantar file CSV sekarang.\n\n"
            "✅ Kolum: `open, high, low, close, volume`\n"
            "• TradingView / Yahoo Finance export OK\n\n"
            "💡 _Token hanya ditolak selepas analisa keluar_\n\n"
            "_(Taip /start untuk Dashboard)_",
            parse_mode='Markdown'
        )
        return STATE_WAITING_CSV

# ─────────────────────────────────────────
# GUIDED CANDLE
# ─────────────────────────────────────────
async def handle_guided_candle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    count = context.user_data.get('candle_count', 5)
    current = context.user_data.get('current_candle', 1)
    ticker = context.user_data.get('ticker', 'SAHAM')
    tf = context.user_data.get('timeframe', 'D')
    tier = context.user_data.get('tier', 0)

    try:
        o, h, l, c, v = parse_candle_values(text.split())
    except ValueError as exc:
        if str(exc) == "logic":
            await update.message.reply_text(
                "❗ *Data tak logik!*\n\nHIGH kena > OPEN & CLOSE\nLOW kena < OPEN & CLOSE\n\n"
                f"Cuba semula *Candle {current}/{count}*:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Tukar Saham",callback_data="tukar_saham"),
                     InlineKeyboardButton("🏠 Dashboard",callback_data="menu_main")]
                ]),
                parse_mode='Markdown'
            )
            return STATE_GUIDED_CANDLE

        if str(exc) == "range":
            await update.message.reply_text(
                "❗ *Data tak valid!*\n\nSemua harga mesti lebih besar dari 0 dan volume tak boleh negatif.\n\n"
                f"Cuba semula *Candle {current}/{count}*:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Tukar Saham",callback_data="tukar_saham"),
                     InlineKeyboardButton("🏠 Dashboard",callback_data="menu_main")]
                ]),
                parse_mode='Markdown'
            )
            return STATE_GUIDED_CANDLE

        await update.message.reply_text(
            "❗ *Format salah!*\n\n`OPEN HIGH LOW CLOSE VOLUME`\n"
            "Contoh: `9.10 9.45 9.05 9.20 980000`\n\n"
            f"Cuba semula *Candle {current}/{count}*:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Tukar Saham",callback_data="tukar_saham"),
                 InlineKeyboardButton("🏠 Dashboard",callback_data="menu_main")]
            ]),
            parse_mode='Markdown'
        )
        return STATE_GUIDED_CANDLE

    candles = context.user_data.get('candles_collected', [])
    candles.append((o,h,l,c,v))
    context.user_data['candles_collected'] = candles

    filled = "🟩" * current
    empty = "⬜" * (count - current)
    progress = f"{filled}{empty}  {current}/{count}"

    if current >= count:
        await send_analysis_result(
            update.message,
            context,
            user_id,
            candles,
            ticker,
            tf,
            tier,
            count,
            'manual',
        )
        return STATE_SAVE
    else:
        next_c = current + 1
        context.user_data['current_candle'] = next_c
        await update.message.reply_text(
            f"✅ *Candle {current}/{count} disimpan!*\n{progress}\n\n"
            f"📊 *Candle {next_c}/{count}*\n\n"
            "`OPEN HIGH LOW CLOSE VOLUME`\n\n"
            "💡 _Token hanya ditolak selepas analisa keluar_",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Tukar Saham",callback_data="tukar_saham"),
                 InlineKeyboardButton("🏠 Dashboard",callback_data="menu_main")]
            ]),
            parse_mode='Markdown'
        )
        return STATE_GUIDED_CANDLE

# ─────────────────────────────────────────
# CSV Upload
# ─────────────────────────────────────────
async def handle_csv_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    count = context.user_data.get('candle_count', 5)
    tf = context.user_data.get('timeframe', 'D')
    tier = context.user_data.get('tier', 0)
    ticker = context.user_data.get('ticker', 'SAHAM')

    if not update.message.document:
        await update.message.reply_text("❗ Hantar file CSV je.")
        return STATE_WAITING_CSV

    if (update.message.document.file_size or 0) > MAX_CSV_SIZE_BYTES:
        await update.message.reply_text("❗ Fail CSV terlalu besar. Maksimum 1MB sahaja.")
        return STATE_WAITING_CSV

    file = await update.message.document.get_file()
    file_bytes = await file.download_as_bytearray()
    if len(file_bytes) > MAX_CSV_SIZE_BYTES:
        await update.message.reply_text("❗ Fail CSV terlalu besar. Maksimum 1MB sahaja.")
        return STATE_WAITING_CSV
    content = file_bytes.decode('utf-8', errors='ignore')

    try:
        reader = csv.DictReader(io.StringIO(content))
        headers = [h.lower().strip() for h in (reader.fieldnames or [])]
        col_map = {}
        for col in ['open','high','low','close','volume']:
            for h in headers:
                if col in h:
                    col_map[col] = h
                    break
        missing = [c for c in ['open','high','low','close','volume'] if c not in col_map]
        if missing:
            await update.message.reply_text(
                f"❗ Kolum tidak jumpa: *{', '.join(missing)}*", parse_mode='Markdown'
            )
            return STATE_WAITING_CSV
        all_rows = list(reader)
        rows = all_rows[-count:]
        if len(rows) < count:
            await update.message.reply_text(
                f"❗ CSV ada {len(all_rows)} baris, perlukan {count}."
            )
            return STATE_WAITING_CSV
        candles = []
        for row in rows:
            o, h, l, c, v = parse_candle_values([
                row[col_map['open']],
                row[col_map['high']],
                row[col_map['low']],
                row[col_map['close']],
                row[col_map['volume']],
            ])
            candles.append((o,h,l,c,v))
    except Exception:
        logging.exception("CSV validation failed for user %s", user_id)
        await update.message.reply_text(
            "❗ Gagal baca CSV. Pastikan fail ada kolum open, high, low, close, volume dan data yang valid."
        )
        return STATE_WAITING_CSV

    await send_analysis_result(
        update.message,
        context,
        user_id,
        candles,
        ticker,
        tf,
        tier,
        count,
        'csv',
    )
    return STATE_SAVE

# ─────────────────────────────────────────
# SAVE FEATURES
# ─────────────────────────────────────────
async def handle_save_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward analisa ke Saved Messages user"""
    query = update.callback_query
    await query.answer()
    result = context.user_data.get('last_result', '')
    ticker = context.user_data.get('last_ticker', 'SAHAM')
    tf = context.user_data.get('last_tf', 'Daily')
    count = context.user_data.get('last_count', 5)
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")

    if not result:
        await query.answer("❗ Tiada data analisa untuk di-forward.", show_alert=True)
        return STATE_SAVE

    save_msg = (
        f"📊 *ANALISA TERSIMPAN — {md(ticker)}*\n"
        f"Timeframe: {md(tf)} | {count} Candle\n"
        f"Masa: {md(timestamp)}\n\n"
        f"{result}\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "💾 Disimpan dari @sahammy2025_bot"
    )

    try:
        # Forward ke Saved Messages (chat_id = user_id)
        await query.bot.send_message(
            chat_id=query.from_user.id,
            text=save_msg,
            parse_mode='Markdown'
        )
        await query.answer("✅ Analisa dah diforward ke Saved Messages kau!", show_alert=True)
    except Exception:
        logging.exception("Failed to forward saved analysis for user %s", query.from_user.id)
        await query.answer("❗ Gagal forward. Cuba download .txt.", show_alert=True)

    return STATE_SAVE

async def handle_save_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hantar analisa sebagai file .txt"""
    query = update.callback_query
    await query.answer()
    result = context.user_data.get('last_result', '')
    ticker = context.user_data.get('last_ticker', 'SAHAM')
    tf = context.user_data.get('last_tf', 'Daily')
    count = context.user_data.get('last_count', 5)
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")

    if not result:
        await query.answer("❗ Tiada data analisa.", show_alert=True)
        return STATE_SAVE

    # Bersihkan markdown untuk txt
    clean_result = result.replace('*','').replace('`','').replace('_','')

    txt_content = (
        f"ANALISA SAHAM — {ticker}\n"
        f"Timeframe: {tf} | {count} Candle\n"
        f"Masa: {timestamp}\n"
        f"{'='*40}\n\n"
        f"{clean_result}\n\n"
        f"{'='*40}\n"
        f"Dijana oleh SahamBot MY\n"
        f"⚠️ Untuk tujuan pembelajaran sahaja. Bukan nasihat pelaburan.\n"
    )

    filename = f"{ticker}_{tf}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    file_obj = io.BytesIO(txt_content.encode('utf-8'))
    file_obj.name = filename

    try:
        await query.bot.send_document(
            chat_id=query.from_user.id,
            document=file_obj,
            filename=filename,
            caption=f"📄 Analisa *{md(ticker)}* — {md(tf)}\n_{md(timestamp)}_",
            parse_mode='Markdown'
        )
        await query.answer("✅ File .txt dah dihantar!", show_alert=True)
    except Exception:
        logging.exception("Failed to send txt analysis for user %s", query.from_user.id)
        await query.answer("❗ Gagal hantar file.", show_alert=True)

    return STATE_SAVE

# ─────────────────────────────────────────
# Cancel
# ─────────────────────────────────────────
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user.id, user.username or user.first_name)
    context.user_data.clear()
    await show_dashboard(update, context, edit=False)
    return STATE_MAIN

# ─────────────────────────────────────────
# Main
# ─────────────────────────────────────────
async def main():
    init_db()
    import os
    TOKEN = os.environ.get("BOT_TOKEN")
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            STATE_MAIN: [CallbackQueryHandler(handle_main_menu)],
            STATE_TICKER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ticker_input)],
            STATE_TIMEFRAME: [
                CallbackQueryHandler(handle_timeframe, pattern="^tf_"),
                CallbackQueryHandler(handle_main_menu, pattern="^menu_|^tukar_"),
            ],
            STATE_CANDLE_COUNT: [
                CallbackQueryHandler(handle_candle_count, pattern="^c_"),
                CallbackQueryHandler(handle_main_menu, pattern="^menu_|^tukar_"),
            ],
            STATE_CANDLE_CONFIRM: [
                CallbackQueryHandler(handle_candle_confirm, pattern="^confirm_"),
                CallbackQueryHandler(handle_main_menu, pattern="^menu_|^tukar_"),
            ],
            STATE_INPUT_METHOD: [
                CallbackQueryHandler(handle_input_method, pattern="^input_"),
                CallbackQueryHandler(handle_main_menu, pattern="^menu_|^tukar_"),
            ],
            STATE_GUIDED_CANDLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guided_candle),
                CallbackQueryHandler(handle_main_menu, pattern="^menu_|^tukar_"),
            ],
            STATE_WAITING_CSV: [
                MessageHandler(filters.Document.ALL, handle_csv_upload),
                CallbackQueryHandler(handle_main_menu, pattern="^menu_|^tukar_"),
            ],
            STATE_SAVE: [
                CallbackQueryHandler(handle_save_forward, pattern="^save_forward$"),
                CallbackQueryHandler(handle_save_txt, pattern="^save_txt$"),
                CallbackQueryHandler(handle_main_menu, pattern="^menu_|^analisa_|^saham_"),
            ],
        },
        fallbacks=[CommandHandler("start", cancel)],
        per_user=True,
        per_chat=True,
    )

    app.add_handler(conv_handler)
    print("✅ SahamBot MY v2.2 running...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("🟢 Bot hidup! Tekan Ctrl+C untuk stop.")
    import asyncio
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
