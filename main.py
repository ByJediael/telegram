import os
import asyncio
import logging
import uvicorn
from dotenv import load_dotenv

import database
import bot
from web_app import app as fastapi_app

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("main")

async def main():
    # 1. Inicializar Banco de Dados
    await database.init_db()
    logger.info("Banco de dados SQLite inicializado com sucesso.")

    # 2. Configurar Bot Telegram
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    bot_application = None

    if token and token != "SEU_TOKEN_AQUI_DO_BOTFATHER":
        try:
            bot_application = bot.create_bot_application(token)
            if bot_application:
                await bot_application.initialize()
                await bot_application.start()
                await bot_application.updater.start_polling(drop_pending_updates=True)
                logger.info("🤖 Bot do Telegram iniciado em modo Polling com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao conectar Bot do Telegram: {e}")
    else:
        logger.warning("⚠️ Token do Telegram não configurado no .env. O bot aguardará a inserção do token pelo Painel Web.")

    # 3. Configurar e rodar Servidor Web FastAPI
    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_PORT", "8000"))

    config = uvicorn.Config(app=fastapi_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    logger.info(f"🌐 Painel Web Admin rodando em: http://localhost:{port}")
    
    try:
        await server.serve()
    finally:
        if bot_application and bot_application.updater.running:
            await bot_application.updater.stop()
            await bot_application.stop()
            await bot_application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
