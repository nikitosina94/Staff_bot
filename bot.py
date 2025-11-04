import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
from db import add_employee, list_employees, mark_attendance, get_attendance_report

# Логи
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))

# Состояния ConversationHandler
MENU, ADD_EMPLOYEE, MARK_ATTENDANCE = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Доступ запрещен!")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("Добавить сотрудника", callback_data="add_employee")],
        [InlineKeyboardButton("Отметить присутствие", callback_data="mark_attendance")],
        [InlineKeyboardButton("Отчет по сотрудникам", callback_data="report")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "add_employee":
        await query.edit_message_text("Введите ФИО сотрудника (через запятую можно добавить должность):")
        return ADD_EMPLOYEE
    elif data == "mark_attendance":
        employees = list_employees()
        if not employees:
            await query.edit_message_text("Список сотрудников пуст.")
            return MENU
        keyboard = [
            [InlineKeyboardButton(emp["name"], callback_data=f"mark_{emp['id']}")]
            for emp in employees
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите сотрудника для отметки:", reply_markup=reply_markup)
        return MARK_ATTENDANCE
    elif data == "report":
        report_text = get_attendance_report()
        await query.edit_message_text(report_text)
        return MENU

async def add_employee_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "," in text:
        name, position = map(str.strip, text.split(",", 1))
    else:
        name = text.strip()
        position = None
    add_employee(name, position)
    await update.message.reply_text(f"Сотрудник {name} добавлен.")
    return await start(update, context)

async def mark_attendance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    emp_id = int(query.data.split("_")[1])
    mark_attendance(emp_id)
    await query.edit_message_text("Отмечено присутствие.")
    return await start(update, context)

def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [CallbackQueryHandler(menu_handler)],
            ADD_EMPLOYEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_employee_handler)],
            MARK_ATTENDANCE: [CallbackQueryHandler(mark_attendance_handler, pattern=r"mark_\d+")],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
