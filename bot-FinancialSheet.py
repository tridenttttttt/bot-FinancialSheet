from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

from dotenv import load_dotenv
import os

# ================= CONFIG =================

SPREADSHEET_NAME = "FinancialSheet_2026"

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name("credenziali_botFinancialSheet.json", scope)
client = gspread.authorize(creds)

sheet_alloc = client.open(SPREADSHEET_NAME).worksheet("Allocation")
sheet_income = client.open(SPREADSHEET_NAME).worksheet("Incomes")
sheet_outcome = client.open(SPREADSHEET_NAME).worksheet("Outcomes")


# ================= WEALTH =================
def get_wealth():
    try:
        return sheet_alloc.acell("B12").value
    except:
        return "0"


# ================= KEYBOARDS =================
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👁 show balance", callback_data="toggle_wealth")],
        [
            InlineKeyboardButton("➕", callback_data="add_income"),
            InlineKeyboardButton("➖", callback_data="add_outcome")
        ]
    ])


def amount_keyboard(mode):
    if mode == "income":
        buttons = ["3.50€", "4.50€", "5.50€", "6.50€"]
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(b, callback_data=f"amt_{b}") for b in buttons],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_home")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="back_home")]
        ])


def confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back", callback_data="retry_amount"),
         InlineKeyboardButton("✅ Confirm", callback_data="confirm_amount")]
    ])


def category_keyboard(mode):
    if mode == "income":
        buttons = [
            ("LABEL 📦", "LABEL"),
            ("TRANSFER 🏦", "TRANSFER"),
            ("FRIENDS/FAMILY 👩‍👩‍👦‍👦", "FRIENDS/FAMILY"),
            ("OTHER", "OTHER")
        ]
    else:
        buttons = [
            ("FOOD 🍽", "FOOD"),
            ("TRANSPORT 🚐", "TRANSPORT"),
            ("TRANSFER 🏦", "TRANSFER"),
            ("SHOPPING 🛍", "SHOPPING"),
            ("FRIENDS/FAMILY 👩‍👩‍👦‍👦", "FRIENDS/FAMILY"),
            ("OTHER", "OTHER")
        ]

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text, callback_data=f"cat_{value}")]
        for text, value in buttons
    ])


def platform_keyboard():
    buttons = ["BYBIT","PAYPAL","HYPE","POSTEIT","KRAK","ISYBANK"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(b, callback_data=f"plat_{b}")]
        for b in buttons
    ])


def description_keyboard(mode):
    if mode == "income":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Label", callback_data="desc_label")]
        ])
    return None


# ================= HOME =================
async def send_home(update, context):

    wealth = get_wealth()
    safe_wealth = wealth.replace("€", "").strip() + " €"
    hide = context.user_data.get("hide_wealth", True)

    display = "•••••••• €" if hide else safe_wealth

    caption = f"Total wealth: {display}"

    msg_id = context.user_data.get("msg_id")

    try:
        with open("logo_FinancialSheet.png", "rb") as photo:
            await context.bot.edit_message_media(
                chat_id=update.effective_chat.id,
                message_id=msg_id,
                media=InputMediaPhoto(photo, caption),
                reply_markup=main_keyboard()
            )
            return
    except:
        with open("logo_FinancialSheet.png", "rb") as photo:
            sent = await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=photo,
                caption=caption,
                reply_markup=main_keyboard()
            )
            context.user_data["msg_id"] = sent.message_id


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hide_wealth"] = True
    await send_home(update, context)


# ================= CALLBACK =================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "toggle_wealth":
        context.user_data["hide_wealth"] = not context.user_data.get("hide_wealth", True)
        await send_home(update, context)

    elif data == "add_income":
        context.user_data["mode"] = "income"
        context.user_data["step"] = "amount"

        await query.edit_message_caption(
            "write or select amount (income)",
            reply_markup=amount_keyboard("income")
        )

    elif data == "add_outcome":
        context.user_data["mode"] = "outcome"
        context.user_data["step"] = "amount"

        await query.edit_message_caption(
            "write amount (outcome)",
            reply_markup=amount_keyboard("outcome")
        )

    elif data == "back_home":
        msg_id = context.user_data.get("msg_id")
        hide = context.user_data.get("hide_wealth", True)

        context.user_data.clear()

        context.user_data["msg_id"] = msg_id
        context.user_data["hide_wealth"] = hide

        await send_home(update, context)

    elif data == "retry_amount":
        mode = context.user_data.get("mode")

        context.user_data["step"] = "amount"

        await query.edit_message_caption(
            "write or select amount",
            reply_markup=amount_keyboard(mode)
        )

    # 🔥 FIX CRUCIALE (MANCAVA)
    elif data.startswith("amt_"):
        raw = data.replace("amt_", "").replace("€", "").replace(",", ".")
        amount = float(raw)

        context.user_data["amount"] = amount
        context.user_data["step"] = "confirm_amount"

        await query.edit_message_caption(
            f"amount selected: {amount:.2f} €",
            reply_markup=confirm_keyboard()
        )

    elif data == "confirm_amount":
        context.user_data["step"] = "category"
        mode = context.user_data.get("mode")

        await query.edit_message_caption(
            "select transaction type",
            reply_markup=category_keyboard(mode)
        )

    elif data.startswith("cat_"):
        context.user_data["category"] = data.replace("cat_", "")
        context.user_data["step"] = "platform"

        await query.edit_message_caption(
            "select payment platform",
            reply_markup=platform_keyboard()
        )

    elif data.startswith("plat_"):
        context.user_data["platform"] = data.replace("plat_", "")
        context.user_data["step"] = "description"

        mode = context.user_data.get("mode")

        await query.edit_message_caption(
            "add payment description",
            reply_markup=description_keyboard(mode)
        )

    elif data == "desc_label":

        msg_id = context.user_data.get("msg_id")
        mode = context.user_data.get("mode")

        today = datetime.now().strftime("%d/%m/%Y")

        row = [
            "",
            today,
            context.user_data["amount"],
            context.user_data["category"],
            context.user_data["platform"],
            "Label"
        ]

        try:
            if mode == "income":
                sheet_income.insert_row(row, index=20)
            else:
                sheet_outcome.insert_row(row, index=20)
        except:
            pass

        context.user_data.clear()
        context.user_data["msg_id"] = msg_id
        context.user_data["hide_wealth"] = True

        await send_home(update, context)


# ================= MESSAGE =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.message
    if not msg:
        return

    text = msg.text

    step = context.user_data.get("step")
    mode = context.user_data.get("mode")

    if step is None:
        return

    try:
        await msg.delete()
    except:
        pass

    # 🔥 FIX CRUCIALE: supporta entrambi gli step
    if step in ["amount", "confirm_amount"]:

        try:
            amount = float(text.replace(",", "."))
            context.user_data["amount"] = amount
            context.user_data["step"] = "confirm_amount"

            await context.bot.edit_message_caption(
                chat_id=update.effective_chat.id,
                message_id=context.user_data["msg_id"],
                caption=f"amount selected: {amount:.2f} €",
                reply_markup=confirm_keyboard()
            )

        except:
            await context.bot.edit_message_caption(
                chat_id=update.effective_chat.id,
                message_id=context.user_data["msg_id"],
                caption="❌ invalid amount",
                reply_markup=amount_keyboard(mode)
            )

        return

    if step == "description":

        today = datetime.now().strftime("%d/%m/%Y")

        row = [
            "",
            today,
            context.user_data["amount"],
            context.user_data["category"],
            context.user_data["platform"],
            text
        ]

        try:
            if mode == "income":
                sheet_income.insert_row(row, index=20)
            else:
                sheet_outcome.insert_row(row, index=20)
        except:
            pass

        msg_id = context.user_data.get("msg_id")

        context.user_data.clear()
        context.user_data["msg_id"] = msg_id
        context.user_data["hide_wealth"] = True

        await send_home(update, context)


# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot avviato...")
app.run_polling()