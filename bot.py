import os
import json
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

import database

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

bot_app: Application = None

def build_inline_keyboard(buttons_list):
    if not buttons_list:
        return None
    keyboard = []
    for btn in buttons_list:
        text = btn.get("text", "Clique Aqui")
        if "url" in btn and btn["url"]:
            keyboard.append([InlineKeyboardButton(text=text, url=btn["url"])])
        elif "callback_data" in btn and btn["callback_data"]:
            keyboard.append([InlineKeyboardButton(text=text, callback_data=btn["callback_data"])])
    return InlineKeyboardMarkup(keyboard) if keyboard else None

async def send_funnel_step(user_id: int, step_number: int, context: ContextTypes.DEFAULT_TYPE, first_name: str = ""):
    step = await database.get_funnel_step(step_number)
    if not step:
        logger.warning(f"Passo {step_number} não encontrado para o usuário {user_id}")
        return False

    msg_text = step["message_text"].replace("{first_name}", first_name or "Amigo(a)")
    keyboard = build_inline_keyboard(step.get("buttons", []))

    try:
        if step.get("media_url"):
            await context.bot.send_photo(
                chat_id=user_id,
                photo=step["media_url"],
                caption=msg_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=msg_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        await database.update_lead_step(user_id, step_number)
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar passo {step_number} para {user_id}: {e}")
        return False

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    # Extrair parâmetro de deep link (ex: /start fb_campanha_01)
    args = context.args
    campaign_source = args[0] if args and len(args) > 0 else "direto"

    logger.info(f"🚀 Comando /start recebido de {user.id} ({user.first_name}) via campanha: {campaign_source}")

    # Salvar lead no banco de dados
    await database.save_or_update_lead(
        telegram_id=user.id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username or "",
        campaign_source=campaign_source
    )

    # Disparar o Passo 1 do Funil
    await send_funnel_step(user.id, 1, context, first_name=user.first_name)

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    text = update.message.text if update.message else ""
    logger.info(f"💬 Mensagem de texto recebida de {user.id} ({user.first_name}): '{text}'")

    # Salvar ou atualizar lead no banco de dados
    await database.save_or_update_lead(
        telegram_id=user.id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username or "",
        campaign_source="direto"
    )

    # Buscar o lead para saber em qual passo ele está ou enviar o passo 1 por padrão
    lead = await database.get_lead_by_telegram_id(user.id)
    current_step = lead.get("current_step", 1) if lead else 1

    await send_funnel_step(user.id, current_step, context, first_name=user.first_name)

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user = update.effective_user

    logger.info(f"👉 Clique de botão do usuário {user.id}: {data}")

    # Se a callback indicar o próximo passo (ex: next_step_2)
    if data.startswith("next_step_"):
        try:
            next_step_num = int(data.replace("next_step_", ""))
            await send_funnel_step(user.id, next_step_num, context, first_name=user.first_name)
        except ValueError:
            pass

async def send_broadcast_message(broadcast_id: int, message_text: str, filter_campaign: str = "all"):
    global bot_app
    if not bot_app or not bot_app.bot:
        logger.error("Bot não inicializado para realizar disparo de broadcast")
        await database.update_broadcast(broadcast_id, 0, "failed")
        return

    leads = await database.get_all_leads(campaign_filter=filter_campaign)
    total = len(leads)
    sent_count = 0

    await database.update_broadcast(broadcast_id, 0, "sending")

    for lead in leads:
        try:
            formatted_text = message_text.replace("{first_name}", lead.get("first_name") or "Amigo(a)")
            await bot_app.bot.send_message(
                chat_id=lead["telegram_id"],
                text=formatted_text,
                parse_mode="Markdown"
            )
            sent_count += 1
            await database.update_broadcast(broadcast_id, sent_count, "sending")
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"Erro ao enviar broadcast para lead {lead['telegram_id']}: {e}")

    await database.update_broadcast(broadcast_id, sent_count, "completed")
    logger.info(f"Broadcast {broadcast_id} finalizado. Sucesso: {sent_count}/{total}")

def create_bot_application(token: str) -> Application:
    global bot_app
    if not token or token == "SEU_TOKEN_AQUI_DO_BOTFATHER":
        logger.warning("TELEGRAM_BOT_TOKEN não configurado. O Bot continuará pausado até o token ser fornecido.")
        return None

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    bot_app = app
    return app
