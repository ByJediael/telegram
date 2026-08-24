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

# Dicionário global para manter as instâncias ativas dos bots {bot_db_id: Application}
active_bots: dict[int, Application] = {}

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

async def send_funnel_step(user_id: int, step_number: int, context: ContextTypes.DEFAULT_TYPE, first_name: str = "", bot_id: int = 1):
    step = await database.get_funnel_step(step_number, bot_id=bot_id)
    if not step:
        logger.warning(f"Passo {step_number} não encontrado para o usuário {user_id} no Bot {bot_id}")
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
        await database.update_lead_step(user_id, bot_id, step_number)
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar passo {step_number} para {user_id} no Bot {bot_id}: {e}")
        return False

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    bot_db_id = context.bot_data.get("bot_db_id", 1)

    # Extrair parâmetro de deep link (ex: /start fb_campanha_01)
    args = context.args
    campaign_source = args[0] if args and len(args) > 0 else "direto"

    logger.info(f"🚀 [Bot #{bot_db_id}] Comando /start recebido de {user.id} ({user.first_name}) via campanha: {campaign_source}")

    # Salvar lead no banco de dados com vinculação ao bot_id
    await database.save_or_update_lead(
        telegram_id=user.id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username or "",
        campaign_source=campaign_source,
        bot_id=bot_db_id
    )

    # Disparar o Passo 1 do Funil
    await send_funnel_step(user.id, 1, context, first_name=user.first_name, bot_id=bot_db_id)

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    bot_db_id = context.bot_data.get("bot_db_id", 1)
    text = update.message.text if update.message else ""
    logger.info(f"💬 [Bot #{bot_db_id}] Mensagem recebida de {user.id} ({user.first_name}): '{text}'")

    # Salvar ou atualizar lead no banco de dados
    await database.save_or_update_lead(
        telegram_id=user.id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username or "",
        campaign_source="direto",
        bot_id=bot_db_id
    )

    lead = await database.get_lead(user.id, bot_id=bot_db_id)
    current_step = lead.get("current_step", 1) if lead else 1

    await send_funnel_step(user.id, current_step, context, first_name=user.first_name, bot_id=bot_db_id)

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user = update.effective_user
    bot_db_id = context.bot_data.get("bot_db_id", 1)

    logger.info(f"👉 [Bot #{bot_db_id}] Clique de botão do usuário {user.id}: {data}")

    if data.startswith("next_step_"):
        try:
            next_step_num = int(data.replace("next_step_", ""))
            await send_funnel_step(user.id, next_step_num, context, first_name=user.first_name, bot_id=bot_db_id)
        except ValueError:
            pass

async def start_bot_instance(bot_db_id: int, token: str) -> Application:
    global active_bots
    if not token:
        return None

    try:
        app = Application.builder().token(token).build()
        app.bot_data["bot_db_id"] = bot_db_id

        app.add_handler(CommandHandler("start", start_handler))
        app.add_handler(CallbackQueryHandler(callback_query_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)

        active_bots[bot_db_id] = app
        logger.info(f"🤖 Bot #{bot_db_id} (@{app.bot.username}) conectado e rodando em modo Polling com sucesso!")
        return app
    except Exception as e:
        logger.error(f"Erro ao inicializar Bot #{bot_db_id}: {e}")
        return None

async def stop_bot_instance(bot_db_id: int):
    global active_bots
    if bot_db_id in active_bots:
        app = active_bots[bot_db_id]
        try:
            if app.updater and app.updater.running:
                await app.updater.stop()
            await app.stop()
            await app.shutdown()
            logger.info(f"🛑 Bot #{bot_db_id} desconectado.")
        except Exception as e:
            logger.error(f"Erro ao parar Bot #{bot_db_id}: {e}")
        finally:
            active_bots.pop(bot_db_id, None)

async def start_all_bots():
    bots_list = await database.get_active_bots()
    logger.info(f"Carregando {len(bots_list)} bot(s) ativo(s) do banco de dados...")
    for bot_data in bots_list:
        await start_bot_instance(bot_data["id"], bot_data["token"])

async def send_broadcast_message(broadcast_id: int, message_text: str, filter_campaign: str = "all", bot_id: int = 0):
    global active_bots
    leads = await database.get_all_leads(campaign_filter=filter_campaign, bot_id=bot_id)
    total = len(leads)
    sent_count = 0

    await database.update_broadcast(broadcast_id, 0, "sending")

    for lead in leads:
        lead_bot_id = lead.get("bot_id")
        target_app = active_bots.get(lead_bot_id) or (list(active_bots.values())[0] if active_bots else None)
        
        if not target_app or not target_app.bot:
            continue

        try:
            formatted_text = message_text.replace("{first_name}", lead.get("first_name") or "Amigo(a)")
            await target_app.bot.send_message(
                chat_id=lead["telegram_id"],
                text=formatted_text,
                parse_mode="Markdown"
            )
            sent_count += 1
            await database.update_broadcast(broadcast_id, sent_count, "sending")
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"Erro ao enviar broadcast para lead {lead['telegram_id']} (Bot #{lead_bot_id}): {e}")

    await database.update_broadcast(broadcast_id, sent_count, "completed")
    logger.info(f"Broadcast {broadcast_id} finalizado. Sucesso: {sent_count}/{total}")
