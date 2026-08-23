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
        
        # Tabela de Leads
        await db.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                campaign_source TEXT DEFAULT 'direto',
                current_step INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de Passos do Funil
        await db.execute("""
            CREATE TABLE IF NOT EXISTS funnel_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                step_number INTEGER UNIQUE NOT NULL,
                title TEXT NOT NULL,
                message_text TEXT NOT NULL,
                media_url TEXT DEFAULT '',
                delay_seconds INTEGER DEFAULT 0,
                buttons_json TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de Disparos em Massa (Broadcasts)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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

        # Inserir funil inicial padrão se a tabela estiver vazia
        async with db.execute("SELECT COUNT(*) as count FROM funnel_steps") as cursor:
            row = await cursor.fetchone()
            if row and row["count"] == 0:
                default_steps = [
                    (
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
                    INSERT INTO funnel_steps (step_number, title, message_text, media_url, delay_seconds, buttons_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, default_steps)
                await db.commit()

async def save_or_update_lead(telegram_id: int, first_name: str, last_name: str, username: str, campaign_source: str = "direto"):
    async with get_db() as db:
        now = datetime.now().isoformat()
        await db.execute("""
            INSERT INTO leads (telegram_id, first_name, last_name, username, campaign_source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                username = excluded.username,
                updated_at = excluded.updated_at
        """, (telegram_id, first_name or "", last_name or "", username or "", campaign_source or "direto", now, now))
        await db.commit()

async def get_lead_by_telegram_id(telegram_id: int):
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM leads WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_lead_step(telegram_id: int, step_number: int):
    async with get_db() as db:
        now = datetime.now().isoformat()
        await db.execute("UPDATE leads SET current_step = ?, updated_at = ? WHERE telegram_id = ?", (step_number, now, telegram_id))
        await db.commit()

async def get_all_leads(campaign_filter: str = "all"):
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        if campaign_filter and campaign_filter != "all":
            query = "SELECT * FROM leads WHERE campaign_source = ? ORDER BY created_at DESC"
            params = (campaign_filter,)
        else:
            query = "SELECT * FROM leads ORDER BY created_at DESC"
            params = ()
            
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_analytics_summary():
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        # Total leads
        async with db.execute("SELECT COUNT(*) as total FROM leads") as cursor:
            total_leads = (await cursor.fetchone())["total"]

        # Leads hoje
        today = datetime.now().strftime("%Y-%m-%d")
        async with db.execute("SELECT COUNT(*) as today FROM leads WHERE created_at LIKE ?", (f"{today}%",)) as cursor:
            leads_today = (await cursor.fetchone())["today"]

        # Origens de Campanhas
        async with db.execute("SELECT campaign_source, COUNT(*) as count FROM leads GROUP BY campaign_source ORDER BY count DESC") as cursor:
            campaigns = [dict(row) for row in await cursor.fetchall()]

        # Funis ativos
        async with db.execute("SELECT COUNT(*) as count FROM funnel_steps") as cursor:
            total_funnel_steps = (await cursor.fetchone())["count"]

        # Total broadcasts
        async with db.execute("SELECT COUNT(*) as count FROM broadcasts") as cursor:
            total_broadcasts = (await cursor.fetchone())["count"]

        return {
            "total_leads": total_leads,
            "leads_today": leads_today,
            "total_steps": total_funnel_steps,
            "total_broadcasts": total_broadcasts,
            "campaigns": campaigns
        }

async def get_funnel_steps():
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM funnel_steps ORDER BY step_number ASC") as cursor:
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

async def get_funnel_step(step_number: int):
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM funnel_steps WHERE step_number = ?", (step_number,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            try:
                item["buttons"] = json.loads(item["buttons_json"])
            except Exception:
                item["buttons"] = []
            return item

async def save_funnel_step(step_number: int, title: str, message_text: str, media_url: str = "", delay_seconds: int = 0, buttons: list = None):
    buttons_json = json.dumps(buttons or [], ensure_ascii=False)
    async with get_db() as db:
        await db.execute("""
            INSERT INTO funnel_steps (step_number, title, message_text, media_url, delay_seconds, buttons_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(step_number) DO UPDATE SET
                title = excluded.title,
                message_text = excluded.message_text,
                media_url = excluded.media_url,
                delay_seconds = excluded.delay_seconds,
                buttons_json = excluded.buttons_json
        """, (step_number, title, message_text, media_url or "", delay_seconds, buttons_json))
        await db.commit()

async def delete_funnel_step(step_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM funnel_steps WHERE id = ?", (step_id,))
        await db.commit()

async def create_broadcast(title: str, message_text: str, filter_campaign: str = "all"):
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        # Calcular total de alvos
        if filter_campaign and filter_campaign != "all":
            async with db.execute("SELECT COUNT(*) as total FROM leads WHERE campaign_source = ?", (filter_campaign,)) as cursor:
                total_target = (await cursor.fetchone())["total"]
        else:
            async with db.execute("SELECT COUNT(*) as total FROM leads") as cursor:
                total_target = (await cursor.fetchone())["total"]

        cursor = await db.execute("""
            INSERT INTO broadcasts (title, message_text, filter_campaign, status, sent_count, total_target)
            VALUES (?, ?, ?, 'pending', 0, ?)
        """, (title, message_text, filter_campaign or "all", total_target))
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
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
