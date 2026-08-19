import os
import asyncio
from datetime import datetime
from collections import defaultdict

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from flask import Flask
import feedparser

# 1. CONFIGURACIÓN ⚙️
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# IDs de tu servidor
ID_CANAL_LOGS = 1534597739189506058
ID_CANAL_BIENVENIDA = 1534589707445469214  # Canal #wlc
ID_CANAL_TIKTOK = 1534602858589065226     # Canal donde avisará los TikToks (cámbialo si quieres otro)
TIKTOK_RSS_URL = https://rss.app/r/feed/DZ8Gveq2eJ3Ph50E  # Tu enlace RSS de TikTok

ROL_AUTOMATICO = "✦ Members" 
COLOR_CELESTE = 0x00FFFF 

intents = discord.Intents.default()
intents.members = True          
intents.message_content = True  
intents.moderation = True       
intents.guilds = True
intents.reactions = True  

bot = commands.Bot(command_prefix="!", intents=intents)
spam_tracker = defaultdict(list)
ultimo_tiktok_id = None


# --- WEB PARA RAILWAY ---
app = Flask('')

@app.route('/')
def home():
    return "Bot esta vivo!"

async def run_web():
    port = int(os.environ.get("PORT", 8080))
    from werkzeug.serving import make_server
    server = make_server('0.0.0.0', port, app)
    print(f"🌐 Servidor web iniciado en el puerto {port}")
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, server.serve_forever)


# --- TAREA AUTOMÁTICA PARA TIKTOK ---
@tasks.loop(minutes=5)
async def check_tiktok_updates():
    global ultimo_tiktok_id
    canal = bot.get_channel(ID_CANAL_TIKTOK)
    if not canal:
        return

    try:
        feed = feedparser.parse(TIKTOK_RSS_URL)
        if not feed.entries:
            return

        latest_entry = feed.entries[0]
        entry_id = latest_entry.get("id", latest_entry.get("link"))

        if ultimo_tiktok_id is None:
            ultimo_tiktok_id = entry_id
            return

        if entry_id != ultimo_tiktok_id:
            ultimo_tiktok_id = entry_id
            titulo = latest_entry.get("title", "¡Nuevo TikTok publicado! 🎬")
            link = latest_entry.get("link", "")

            await canal.send(f"🚨 **¡Nuevo TikTok!** <@&1539717338331619358> 🎥\n{titulo}\n{link}")
            print(f"✅ Notificación de TikTok enviada: {link}")

    except Exception as e:
        print(f"❌ Error al verificar el RSS de TikTok: {e}")

@check_tiktok_updates.before_loop
async def before_tiktok_task():
    await bot.wait_until_ready()


# --- FUNCIÓN DE LOGS ---
async def send_log_embed(action_title, target_obj, color, description, is_generic=False):
    log_channel = bot.get_channel(ID_CANAL_LOGS)
    if not log_channel: return
    embed = discord.Embed(color=color, description=description)
    
    if is_generic:
        icon = target_obj.guild.icon.url if target_obj.guild.icon else None
        embed.set_author(name="PAPUDADO", icon_url=icon) 
    else:
        embed.set_author(name=action_title, icon_url=target_obj.display_avatar.url)
        
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
    embed.set_footer(text=f"ID: {target_obj.id} • {fecha_actual}")
    await log_channel.send(embed=embed)


# --- ASIGNACIÓN AUTOMÁTICA DE ROL AL ENTRAR ---
@bot.event
async def on_member_join(member):
    print(f"📥 {member.name} se ha unido al servidor. Asignando rol '{ROL_AUTOMATICO}'...")
    
    role = discord.utils.get(member.guild.roles, name=ROL_AUTOMATICO)
    
    if not role:
        print(f"❌ ERROR: No existe ningún rol llamado exactamente '{ROL_AUTOMATICO}' en el servidor.")
        return

    try:
        await member.add_roles(role)
        print(f"✅ ÉXITO: ¡Rol '{ROL_AUTOMATICO}' dado automáticamente a {member.name}!")
    except discord.Forbidden:
        print(f"❌ ERROR DE DISCORD: El bot no tiene el permiso 'Gestionar Roles' o su rol está por DEBAJO de '{ROL_AUTOMATICO}'.")
    except Exception as e:
        print(f"❌ Error inesperado al dar rol automático: {e}")


# --- EVENTOS DE USUARIOS (EXPULSIONES Y ACTUALIZACIÓN DE RANGOS) ---
@bot.event
async def on_member_remove(member):
    await asyncio.sleep(1)
    try:
        async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=5):
            if entry.target.id == member.id and (datetime.now(entry.created_at.tzinfo) - entry.created_at).total_seconds() < 10:
                await send_log_embed("User Kicked", member, 0xff4500, f"{member.mention} **was kicked** ✅")
                return
    except Exception as e:
        print(f"Error al revisar los logs de expulsión: {e}")

@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        if len(before.roles) > len(after.roles):
            roles_quitados = [r for r in before.roles if r not in after.roles]
            for rol in roles_quitados:
                desc = f"{after.mention} > **{rol.name}** was removed"
                await send_log_embed("Role Removed", after, 0xe74c3c, desc)
        
        elif len(after.roles) > len(before.roles):
            roles_dados = [r for r in after.roles if r not in before.roles]
            for rol in roles_dados:
                desc = f"{after.mention} > **{rol.name}** was given"
                await send_log_embed("Role Given", after, 0x3498db, desc)


# --- MODERACIÓN (BANEOS) ---
@bot.event
async def on_member_ban(guild, user):
    await send_log_embed("User Banned", user, 0xff0000, f"{user.mention} **was banned** ✅")


# --- EVENTOS DE CANALES (CREAR/BORRAR) ---
@bot.event
async def on_guild_channel_create(channel):
    await send_log_embed("PAPUDADO", channel, 0x2ecc71, f"Channel Create: **#{channel.name}**", is_generic=True)

@bot.event
async def on_guild_channel_delete(channel):
    await send_log_embed("PAPUDADO", channel, 0xff0000, f"Channel Delete: **#{channel.name}**", is_generic=True)


# --- EVENTOS DE ROLES (CREAR/BORRAR/EDITAR) ---
@bot.event
async def on_guild_role_create(role):
    await send_log_embed("PAPUDADO", role, 0x2ecc71, f"**Role Created: {role.name}**", is_generic=True)

@bot.event
async def on_guild_role_delete(role):
    await send_log_embed("PAPUDADO", role, 0xff0000, f"**Role Deleted: {role.name}**", is_generic=True)

@bot.event
async def on_guild_role_update(before, after):
    if before.permissions != after.permissions:
        old_perms = dict(before.permissions)
        new_perms = dict(after.permissions)
        added = [f"**{p.replace('_', ' ').title()}**" for p, v in new_perms.items() if v and not old_perms[p]]
        removed = [f"**{p.replace('_', ' ').title()}**" for p, v in old_perms.items() if v and not new_perms[p]]
        if added or removed:
            desc = f"Role: **{after.name}**\n"
            if added: desc += f"✅ Added: {', '.join(added)}\n"
            if removed: desc += f"❌ Removed: {', '.join(removed)}"
            await send_log_embed("PAPUDADO", after, 0xf1c40f, desc, is_generic=True)


# --- ANTI-SPAM ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    now = asyncio.get_event_loop().time()
    user_id = message.author.id
    spam_tracker[user_id].append(now)
    spam_tracker[user_id] = [t for t in spam_tracker[user_id] if now - t < 10]
    if len(spam_tracker[user_id]) > 20:
        try: await message.delete()
        except: pass
        return
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} online. Configuración para PAPUDADO activa.")
    if not check_tiktok_updates.is_running():
        check_tiktok_updates.start()


# --- ARRANQUE DUAL ASÍNCRONO ---
async def main():
    await asyncio.gather(
        run_web(),
        bot.start(TOKEN)
    )

if __name__ == "__main__":
    asyncio.run(main())
