import aiosqlite
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "telegram_bot.db")

def get_db():
    return aiosqlite.connect(DB_PATH)

async def init_db():
    async with get_db() as db:
        db.row_factory = aiosqlite.Row

        # Tabela de Bots Conectados
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                username TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela de Leads (vinculados ao bot_id)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                bot_id INTEGER DEFAULT 1,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                campaign_source TEXT DEFAULT 'direto',
                current_step INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(telegram_id, bot_id)
            )
        """)

        # Tabela de Passos do Funil (bot_id = 0 significa Funil Global Padrão)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS funnel_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER DEFAULT 0,
                step_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                message_text TEXT NOT NULL,
                media_url TEXT DEFAULT '',
                delay_seconds INTEGER DEFAULT 0,
                buttons_json TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(bot_id, step_number)
            )
        """)

        # Tabela de Disparos em Massa (bot_id = 0 para Todos os Bots)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER DEFAULT 0,
                title TEXT NOT NULL,
                message_text TEXT NOT NULL,
                filter_campaign TEXT DEFAULT 'all',
                status TEXT DEFAULT 'pending',
                sent_count INTEGER DEFAULT 0,
                total_target INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.commit()

        # Se houver token legado no arquivo .env, migrar para a tabela de bots
        load_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if load_token and load_token != "SEU_TOKEN_AQUI_DO_BOTFATHER":
            async with db.execute("SELECT COUNT(*) as count FROM bots WHERE token = ?", (load_token,)) as cursor:
                row = await cursor.fetchone()
                if row and row["count"] == 0:
                    import urllib.request
                    try:
                        url = f"https://api.telegram.org/bot{load_token}/getMe"
                        req = urllib.request.urlopen(url, timeout=3)
                        res = json.loads(req.read().decode())
                        if res.get("ok"):
                            bot_res = res.get("result")
                            await db.execute(
                                "INSERT INTO bots (token, name, username, status) VALUES (?, ?, ?, 'active')",
                                (load_token, bot_res.get("first_name", "Bot Telegram"), bot_res.get("username", ""))
                            )
                            await db.commit()
                    except Exception:
                        pass

        # Inserir funil inicial padrão (Global bot_id = 0) se a tabela estiver vazia
        async with db.execute("SELECT COUNT(*) as count FROM funnel_steps WHERE bot_id = 0") as cursor:
            row = await cursor.fetchone()
            if row and row["count"] == 0:
                default_steps = [
                    (
                        0,
                        1,
                        "Passo 1: Boas-Vindas & Qualificação",
                        "👋 Olá {first_name}! Seja muito bem-vindo(a)!\n\nIdentificamos que você chegou até nós através da nossa campanha de tráfego.\n\nComo podemos te ajudar hoje?",
                        "",
                        0,
                        json.dumps([
                            {"text": "🔥 Conhecer a Oferta Especial", "callback_data": "next_step_2"},
                            {"text": "💬 Falar com Atendimento", "url": "https://t.me/telegram"}
                        ], ensure_ascii=False)
                    ),
                    (
                        0,
                        2,
                        "Passo 2: Apresentação da Oferta",
                        "🚀 **Aqui está o nosso produto exclusivo!**\n\nCriamos um método completo para alavancar os seus resultados sem riscos de bloqueio.\n\nClique no botão abaixo para acessar o conteúdo especial preparado para você:",
                        "",
                        0,
                        json.dumps([
                            {"text": "👉 Acessar Oferta Agora", "url": "https://google.com"}
                        ], ensure_ascii=False)
                    )
                ]
                await db.executemany("""
                    INSERT INTO funnel_steps (bot_id, step_number, title, message_text, media_url, delay_seconds, buttons_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, default_steps)
                await db.commit()

# --- GESTÃO DE BOTS ---

async def get_all_bots():
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bots ORDER BY created_at DESC") as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def get_active_bots():
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bots WHERE status = 'active'") as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def save_bot(token: str, name: str, username: str):
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("""
            INSERT INTO bots (token, name, username, status)
            VALUES (?, ?, ?, 'active')
            ON CONFLICT(token) DO UPDATE SET
                name = excluded.name,
                username = excluded.username,
                status = 'active'
        """, (token, name, username))
        await db.commit()

async def delete_bot(bot_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
        await db.commit()

async def toggle_bot_status(bot_id: int, status: str):
    async with get_db() as db:
        await db.execute("UPDATE bots SET status = ? WHERE id = ?", (status, bot_id))
        await db.commit()

# --- GESTÃO DE LEADS ---

async def save_or_update_lead(telegram_id: int, first_name: str, last_name: str, username: str, campaign_source: str = "direto", bot_id: int = 1):
    async with get_db() as db:
        now = datetime.now().isoformat()
        await db.execute("""
            INSERT INTO leads (telegram_id, bot_id, first_name, last_name, username, campaign_source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id, bot_id) DO UPDATE SET
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                username = excluded.username,
                updated_at = excluded.updated_at
        """, (telegram_id, bot_id, first_name or "", last_name or "", username or "", campaign_source or "direto", now, now))
        await db.commit()

async def get_lead(telegram_id: int, bot_id: int = 1):
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM leads WHERE telegram_id = ? AND bot_id = ?", (telegram_id, bot_id)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_lead_step(telegram_id: int, bot_id: int, step_number: int):
    async with get_db() as db:
        now = datetime.now().isoformat()
        await db.execute("UPDATE leads SET current_step = ?, updated_at = ? WHERE telegram_id = ? AND bot_id = ?", (step_number, now, telegram_id, bot_id))
        await db.commit()

async def get_all_leads(campaign_filter: str = "all", bot_id: int = 0):
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT l.*, b.name as bot_name, b.username as bot_username FROM leads l LEFT JOIN bots b ON l.bot_id = b.id WHERE 1=1"
        params = []

        if bot_id and int(bot_id) > 0:
            query += " AND l.bot_id = ?"
            params.append(int(bot_id))

        if campaign_filter and campaign_filter != "all":
            query += " AND l.campaign_source = ?"
            params.append(campaign_filter)

        query += " ORDER BY l.created_at DESC"
        async with db.execute(query, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

# --- METRICAS & STATS ---

async def get_analytics_summary(bot_id: int = 0):
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        bot_filter = " WHERE bot_id = ?" if bot_id and int(bot_id) > 0 else ""
        params = (int(bot_id),) if bot_id and int(bot_id) > 0 else ()

        # Total leads
        async with db.execute(f"SELECT COUNT(*) as total FROM leads{bot_filter}", params) as cursor:
            total_leads = (await cursor.fetchone())["total"]

        # Leads hoje
        today = datetime.now().strftime("%Y-%m-%d")
        today_filter = f" WHERE created_at LIKE '{today}%'" + (f" AND bot_id = {int(bot_id)}" if bot_id and int(bot_id) > 0 else "")
        async with db.execute(f"SELECT COUNT(*) as today FROM leads{today_filter}") as cursor:
            leads_today = (await cursor.fetchone())["today"]

        # Origens de Campanhas
        async with db.execute(f"SELECT campaign_source, COUNT(*) as count FROM leads{bot_filter} GROUP BY campaign_source ORDER BY count DESC", params) as cursor:
            campaigns = [dict(row) for row in await cursor.fetchall()]

        # Passos de funil
        step_filter = f" WHERE bot_id = {int(bot_id)}" if bot_id and int(bot_id) > 0 else " WHERE bot_id = 0"
        async with db.execute(f"SELECT COUNT(*) as count FROM funnel_steps{step_filter}") as cursor:
            total_funnel_steps = (await cursor.fetchone())["count"]

        # Total broadcasts
        async with db.execute("SELECT COUNT(*) as count FROM broadcasts") as cursor:
            total_broadcasts = (await cursor.fetchone())["count"]

        # Lista de bots ativos
        bots = await get_all_bots()

        return {
            "total_leads": total_leads,
            "leads_today": leads_today,
            "total_steps": total_funnel_steps,
            "total_broadcasts": total_broadcasts,
            "total_bots": len(bots),
            "campaigns": campaigns,
            "bots": bots
        }

# --- FUNIS DE VENDAS (GLOBAL bot_id=0 OU CUSTOMIZADO bot_id>0) ---

async def get_funnel_steps(bot_id: int = 0):
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        
        # Verificar se existem passos específicos para este bot
        if bot_id and int(bot_id) > 0:
            async with db.execute("SELECT COUNT(*) as count FROM funnel_steps WHERE bot_id = ?", (int(bot_id),)) as cursor:
                count = (await cursor.fetchone())["count"]
                if count > 0:
                    target_bot_id = int(bot_id)
                else:
                    target_bot_id = 0 # Usar funil global padrão
        else:
            target_bot_id = 0

        async with db.execute("SELECT * FROM funnel_steps WHERE bot_id = ? ORDER BY step_number ASC", (target_bot_id,)) as cursor:
            rows = await cursor.fetchall()
            steps = []
            for row in rows:
                item = dict(row)
                try:
                    item["buttons"] = json.loads(item["buttons_json"])
                except Exception:
                    item["buttons"] = []
                steps.append(item)
            return steps

async def get_funnel_step(step_number: int, bot_id: int = 0):
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        target_bot_id = 0
        if bot_id and int(bot_id) > 0:
            async with db.execute("SELECT COUNT(*) as count FROM funnel_steps WHERE bot_id = ?", (int(bot_id),)) as cursor:
                if (await cursor.fetchone())["count"] > 0:
                    target_bot_id = int(bot_id)

        async with db.execute("SELECT * FROM funnel_steps WHERE bot_id = ? AND step_number = ?", (target_bot_id, step_number)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            try:
                item["buttons"] = json.loads(item["buttons_json"])
            except Exception:
                item["buttons"] = []
            return item

async def save_funnel_step(step_number: int, title: str, message_text: str, media_url: str = "", delay_seconds: int = 0, buttons: list = None, bot_id: int = 0):
    buttons_json = json.dumps(buttons or [], ensure_ascii=False)
    async with get_db() as db:
        await db.execute("""
            INSERT INTO funnel_steps (bot_id, step_number, title, message_text, media_url, delay_seconds, buttons_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(bot_id, step_number) DO UPDATE SET
                title = excluded.title,
                message_text = excluded.message_text,
                media_url = excluded.media_url,
                delay_seconds = excluded.delay_seconds,
                buttons_json = excluded.buttons_json
        """, (int(bot_id), step_number, title, message_text, media_url or "", delay_seconds, buttons_json))
        await db.commit()

async def delete_funnel_step(step_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM funnel_steps WHERE id = ?", (step_id,))
        await db.commit()

# --- BROADCASTS MULTI-BOT ---

async def create_broadcast(title: str, message_text: str, filter_campaign: str = "all", bot_id: int = 0):
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT COUNT(*) as total FROM leads WHERE 1=1"
        params = []
        if bot_id and int(bot_id) > 0:
            query += " AND bot_id = ?"
            params.append(int(bot_id))
        if filter_campaign and filter_campaign != "all":
            query += " AND campaign_source = ?"
            params.append(filter_campaign)

        async with db.execute(query, params) as cursor:
            total_target = (await cursor.fetchone())["total"]

        cursor = await db.execute("""
            INSERT INTO broadcasts (bot_id, title, message_text, filter_campaign, status, sent_count, total_target)
            VALUES (?, ?, ?, ?, 'pending', 0, ?)
        """, (int(bot_id), title, message_text, filter_campaign or "all", total_target))
        await db.commit()
        return cursor.lastrowid

async def update_broadcast(broadcast_id: int, sent_count: int, status: str):
    async with get_db() as db:
        await db.execute("""
            UPDATE broadcasts SET sent_count = ?, status = ? WHERE id = ?
        """, (sent_count, status, broadcast_id))
        await db.commit()

async def get_all_broadcasts():
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM broadcasts ORDER BY created_at DESC") as cursor:
            return [dict(row) for row in await cursor.fetchall()]
