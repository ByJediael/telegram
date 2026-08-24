import os
import json
import urllib.request
import asyncio
from dotenv import load_dotenv, set_key
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import database
import bot

load_dotenv()

app = FastAPI(title="TeleFlow Multi-Bot Platform")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Models
class BotModel(BaseModel):
    token: str

class FunnelStepModel(BaseModel):
    bot_id: int = 0
    step_number: int
    title: str
    message_text: str
    media_url: str = ""
    delay_seconds: int = 0
    buttons: list = []

class BroadcastModel(BaseModel):
    bot_id: int = 0
    title: str
    message_text: str
    filter_campaign: str = "all"

@app.on_event("startup")
async def startup_event():
    await database.init_db()

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/stats")
async def get_stats(bot_id: int = 0):
    summary = await database.get_analytics_summary(bot_id=bot_id)
    return {"summary": summary}

@app.get("/api/bots")
async def list_bots():
    bots_list = await database.get_all_bots()
    return {"bots": bots_list}

@app.post("/api/bots")
async def add_bot(data: BotModel):
    token = data.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token inválido")
    
    # Validar token na API do Telegram
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        req = urllib.request.urlopen(url, timeout=5)
        res = json.loads(req.read().decode())
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail="Token recusado pela API do Telegram")
        bot_res = res.get("result")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao conectar ao Telegram: {str(e)}")

    name = bot_res.get("first_name", "Bot Telegram")
    username = bot_res.get("username", "")

    # Salvar no banco
    await database.save_bot(token=token, name=name, username=username)
    bots_list = await database.get_all_bots()
    saved_bot = next((b for b in bots_list if b["token"] == token), None)

    # Iniciar bot em segundo plano
    if saved_bot:
        await bot.start_bot_instance(saved_bot["id"], token)

    return {"success": True, "bot": saved_bot, "message": f"Bot @{username} adicionado e conectado com sucesso!"}

@app.delete("/api/bots/{bot_id}")
async def remove_bot(bot_id: int):
    await bot.stop_bot_instance(bot_id)
    await database.delete_bot(bot_id)
    return {"success": True, "message": "Bot removido com sucesso!"}

@app.get("/api/leads")
async def list_leads(campaign: str = "all", bot_id: int = 0):
    leads = await database.get_all_leads(campaign_filter=campaign, bot_id=bot_id)
    return {"leads": leads}

@app.get("/api/funnel")
async def list_funnel(bot_id: int = 0):
    steps = await database.get_funnel_steps(bot_id=bot_id)
    return {"steps": steps}

@app.post("/api/funnel")
async def save_funnel(step_data: FunnelStepModel):
    await database.save_funnel_step(
        bot_id=step_data.bot_id,
        step_number=step_data.step_number,
        title=step_data.title,
        message_text=step_data.message_text,
        media_url=step_data.media_url,
        delay_seconds=step_data.delay_seconds,
        buttons=step_data.buttons
    )
    return {"success": True, "message": f"Passo {step_data.step_number} salvo com sucesso!"}

@app.delete("/api/funnel/{step_id}")
async def delete_funnel(step_id: int):
    await database.delete_funnel_step(step_id)
    return {"success": True, "message": "Passo do funil removido!"}

@app.get("/api/broadcasts")
async def list_broadcasts():
    broadcasts = await database.get_all_broadcasts()
    return {"broadcasts": broadcasts}

@app.post("/api/broadcast")
async def launch_broadcast(data: BroadcastModel):
    broadcast_id = await database.create_broadcast(
        title=data.title,
        message_text=data.message_text,
        filter_campaign=data.filter_campaign,
        bot_id=data.bot_id
    )
    
    asyncio.create_task(
        bot.send_broadcast_message(
            broadcast_id=broadcast_id,
            message_text=data.message_text,
            filter_campaign=data.filter_campaign,
            bot_id=data.bot_id
        )
    )
    
    return {"success": True, "broadcast_id": broadcast_id, "message": "Disparo iniciado em segundo plano!"}

@app.post("/api/test-token")
async def test_token(data: BotModel):
    token = data.token.strip()
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        req = urllib.request.urlopen(url, timeout=5)
        res = json.loads(req.read().decode())
        if res.get("ok"):
            bot_res = res.get("result")
            return {
                "valid": True,
                "bot_name": bot_res.get("first_name"),
                "username": bot_res.get("username")
            }
    except Exception as e:
        return {"valid": False, "error": str(e)}
    return {"valid": False, "error": "Token inválido"}
