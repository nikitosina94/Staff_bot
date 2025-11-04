import logging
import os
import calendar
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, InputFile
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters,
    CallbackQueryHandler, ConversationHandler
)
from db import (
    init_db, add_employee, get_employees, mark_attendance,
    get_attendance_report, delete_employee, get_employee_history
)
from report_utils import save_report_xlsx, save_report_pdf

logging.basicConfig(level=logging.INFO)

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

ADD_NAME, ADD_POSITION, MARK_SELECT_EMP, MARK_DATE, MARK_CHOICE, DELETE_SELECT, REPORT_MONTH, EMP_HISTORY = range(8)


async def check_admin(update: Update):
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("🚫 У вас нет доступа.")
        return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return
    keyboard = [
        ["➕ Добавить сотрудника", "❌ Удалить сотрудника"],
        ["✅ Отметить присутствие"],
        ["📊 Отчёт по сотрудникам", "📜 История сотрудника"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)


# --- Добавление сотрудника ---
async def add_employee_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return ConversationHandler.END
    await update.message.reply_text("Введите ФИО сотрудника:")
    return ADD_NAME


async def add_employee_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Введите должность (или '-' если нет):")
    return ADD_POSITION


async def add_employee_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    position = update.message.text
    if position == "-":
        position = None
    add_employee(context.user_data["name"], position)
    await update.message.reply_text("✅ Сотрудник добавлен!")
    return ConversationHandler.END


# --- Удаление сотрудника ---
async def delete_employee_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    employees = get_employees()
    if not employees:
        await update.message.reply_text("Список сотрудников пуст.")
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(emp.name, callback_data=f"del_{emp.id}")]
                for emp in employees]
    await update.message.reply_text("Выберите сотрудника для удаления:",
                                    reply_markup=InlineKeyboardMarkup(keyboard))
    return DELETE_SELECT


async def delete_employee_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    emp_id = int(query.data.split("_")[1])
    delete_employee(emp_id)
    await query.edit_message_text("🗑 Сотрудник удалён.")
    return ConversationHandler.END


# --- Отметка присутствия ---
async def mark_attendance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    employees = get_employees()
    if not employees:
        await update.message.reply_text("Список сотрудников пуст.")
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(emp.name, callback_data=f"mark_{emp.id}")]
                for emp in employees]
    await update.message.reply_text("Выберите сотрудника:", reply_markup=InlineKeyboardMarkup(keyboard))
    return MARK_SELECT_EMP


async def mark_attendance_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    emp_id = int(query.data.split("_")[1])
    context.user_data["emp_id"] = emp_id

    keyboard = [
        [
            InlineKeyboardButton("📅 Сегодня", callback_data="mark_today"),
            InlineKeyboardButton("📆 Другая дата", callback_data="mark_other")
        ]
    ]
    await query.edit_message_text(
        "Выберите способ отметки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MARK_CHOICE


async def mark_attendance_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    choice = query.data
    emp_id = context.user_data["emp_id"]

    if choice == "mark_today":
        mark_attendance(emp_id)
        await query.edit_message_text("✅ Присутствие отмечено на сегодняшний день!")
        return ConversationHandler.END

    if choice == "mark_other":
        await query.edit_message_text("Введите дату (в формате ГГГГ-ММ-ДД):")
        return MARK_DATE


async def mark_attendance_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    emp_id = context.user_data["emp_id"]
    try:
        day = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        await update.message.reply_text("❗ Неверный формат даты. Пример: 2025-11-04")
        return MARK_DATE
    mark_attendance(emp_id, day)
    await update.message.reply_text(f"✅ Присутствие отмечено за {day.strftime('%Y-%m-%d')}!")
    return ConversationHandler.END


# --- Отчёт ---
async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    months = [
        [InlineKeyboardButton(calendar.month_abbr[i], callback_data=f"rep_month_{i}")]
        for i in range(1, 13)
    ]
    await update.message.reply_text("📅 Выберите месяц:", reply_markup=InlineKeyboardMarkup(months))
    return REPORT_MONTH


async def report_month_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    month = int(query.data.split("_")[2])
    context.user_data["month"] = month

    year_now = datetime.now().year
    years = [
        [
            InlineKeyboardButton(str(year_now - 1), callback_data=f"rep_year_{year_now - 1}"),
            InlineKeyboardButton(str(year_now), callback_data=f"rep_year_{year_now}")
        ],
        [InlineKeyboardButton("📊 За всё время", callback_data="rep_year_all")]
    ]
    await query.edit_message_text("📆 Выберите год:", reply_markup=InlineKeyboardMarkup(years))
    return REPORT_MONTH


async def report_year_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    if data[2] == "all":
        month, year = None, None
    else:
        month = context.user_data["month"]
        year = int(data[2])

    report = get_attendance_report(month, year)
    if not report:
        await query.edit_message_text("Нет данных для отчёта.")
        return ConversationHandler.END

    msg = f"📊 Отчёт за {calendar.month_name[month] if month else 'все месяцы'} {year or ''}\n\n"
    for r in report:
        msg += f"👤 {r['name']} ({r['position'] or 'Без должности'})\n" \
               f"📅 {', '.join(r['days']) or '—'}\n🔢 Смен: {r['total']}\n\n"

    await query.edit_message_text(msg)

    xlsx_path = save_report_xlsx(report)
    pdf_path = save_report_pdf(report)
    await query.message.reply_document(InputFile(xlsx_path))
    await query.message.reply_document(InputFile(pdf_path))
    return ConversationHandler.END


# --- История сотрудника ---
async def employee_history_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    employees = get_employees()
    if not employees:
        await update.message.reply_text("Список сотрудников пуст.")
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(emp.name, callback_data=f"hist_{emp.id}")]
                for emp in employees]
    await update.message.reply_text("📜 Выберите сотрудника:", reply_markup=InlineKeyboardMarkup(keyboard))
    return EMP_HISTORY


async def employee_history_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    emp_id = int(query.data.split("_")[1])
    history = get_employee_history(emp_id)
    if not history or not history["days"]:
        await query.edit_message_text("Нет данных по сменам.")
        return ConversationHandler.END
    msg = f"📜 История сотрудника {history['name']} ({history['position'] or 'Без должности'})\n\n" \
          f"📅 {', '.join(history['days'])}\n🔢 Всего смен: {history['total']}"
    await query.edit_message_text(msg)
    return ConversationHandler.END


def main():
    init_db()
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    conv_add = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("➕ Добавить сотрудника"), add_employee_start)],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_employee_name)],
            ADD_POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_employee_position)]
        },
        fallbacks=[]
    )

    conv_delete = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("❌ Удалить сотрудника"), delete_employee_start)],
        states={DELETE_SELECT: [CallbackQueryHandler(delete_employee_confirm)]},
        fallbacks=[]
    )

    conv_mark = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("✅ Отметить присутствие"), mark_attendance_start)],
        states={
            MARK_SELECT_EMP: [CallbackQueryHandler(mark_attendance_select)],
            MARK_CHOICE: [CallbackQueryHandler(mark_attendance_choice, pattern=r"^mark_")],
            MARK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, mark_attendance_date)],
        },
        fallbacks=[]
    )

    conv_report = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("📊 Отчёт по сотрудникам"), report_start)],
        states={
            REPORT_MONTH: [
                CallbackQueryHandler(report_month_select, pattern=r"^rep_month_"),
                CallbackQueryHandler(report_year_select, pattern=r"^rep_year_")
            ]
        },
        fallbacks=[]
    )

    conv_history = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("📜 История сотрудника"), employee_history_start)],
        states={EMP_HISTORY: [CallbackQueryHandler(employee_history_show)]},
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_add)
    app.add_handler(conv_delete)
    app.add_handler(conv_mark)
    app.add_handler(conv_report)
    app.add_handler(conv_history)

    app.run_polling()


if __name__ == "__main__":
    main()
