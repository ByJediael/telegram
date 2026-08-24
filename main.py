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
    # 1. Inicializar Banco de Dados SQLite
    await database.init_db()
    logger.info("⚡ Banco de dados SQLite inicializado com sucesso.")

    # 2. Conectar e iniciar TODOS os Bots cadastrados
    try:
        await bot.start_all_bots()
    except Exception as e:
        logger.error(f"Erro ao inicializar bots do Telegram: {e}")

    # 3. Rodar Servidor Web FastAPI
    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_PORT", "8000"))

    config = uvicorn.Config(app=fastapi_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    logger.info(f"🌐 Painel Web Multi-Bot rodando em: http://localhost:{port}")
    
    try:
        await server.serve()
    finally:
        logger.info("Desconectando bots...")
        for bot_id in list(bot.active_bots.keys()):
            await bot.stop_bot_instance(bot_id)

if __name__ == "__main__":
    asyncio.run(main())
