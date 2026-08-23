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

app = FastAPI(title="Telegram Marketing Funnel Admin")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Models
class FunnelStepModel(BaseModel):
    step_number: int
    title: str
    message_text: str
    media_url: str = ""
    delay_seconds: int = 0
    buttons: list = []

class BroadcastModel(BaseModel):
    title: str
    message_text: str
    filter_campaign: str = "all"

class TokenModel(BaseModel):
    token: str

@app.on_event("startup")
async def startup_event():
    await database.init_db()

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/stats")
async def get_stats():
    summary = await database.get_analytics_summary()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    is_token_set = bool(token and token != "SEU_TOKEN_AQUI_DO_BOTFATHER")
    
    bot_info = None
    if is_token_set:
        try:
            url = f"https://api.telegram.org/bot{token}/getMe"
            req = urllib.request.urlopen(url, timeout=3)
            res = json.loads(req.read().decode())
            if res.get("ok"):
                bot_info = res.get("result")
        except Exception:
            pass

    return {
        "status": "online" if is_token_set and bot_info else "attention_required",
        "bot_info": bot_info,
        "is_token_set": is_token_set,
        "summary": summary
    }

@app.get("/api/leads")
async def list_leads(campaign: str = "all"):
    leads = await database.get_all_leads(campaign_filter=campaign)
    return {"leads": leads}

@app.get("/api/funnel")
async def list_funnel():
    steps = await database.get_funnel_steps()
    return {"steps": steps}

@app.post("/api/funnel")
async def save_funnel(step_data: FunnelStepModel):
    await database.save_funnel_step(
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
    return {"success": True, "message": "Passo removido com sucesso!"}

@app.get("/api/broadcasts")
async def list_broadcasts():
    broadcasts = await database.get_all_broadcasts()
    return {"broadcasts": broadcasts}

@app.post("/api/broadcast")
async def launch_broadcast(data: BroadcastModel):
    broadcast_id = await database.create_broadcast(
        title=data.title,
        message_text=data.message_text,
        filter_campaign=data.filter_campaign
    )
    
    # Executar o disparo em segundo plano
    asyncio.create_task(
        bot.send_broadcast_message(
            broadcast_id=broadcast_id,
            message_text=data.message_text,
            filter_campaign=data.filter_campaign
        )
    )
    
    return {"success": True, "broadcast_id": broadcast_id, "message": "Disparo em massa iniciado em segundo plano!"}

@app.post("/api/settings/token")
async def update_token(data: TokenModel):
    new_token = data.token.strip()
    if not new_token:
        raise HTTPException(status_code=400, detail="Token inválido")
    
    env_path = os.path.join(BASE_DIR, ".env")
    set_key(env_path, "TELEGRAM_BOT_TOKEN", new_token)
    os.environ["TELEGRAM_BOT_TOKEN"] = new_token
    
    return {"success": True, "message": "Token atualizado no arquivo .env! Reinicie a aplicação para conectar o bot."}

@app.post("/api/test-token")
async def test_token(data: TokenModel):
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
    return {"valid": False, "error": "Resposta inválida da API do Telegram"}
