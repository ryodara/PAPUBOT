import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from collections import defaultdict
import time

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Configuración del Bot con los permisos necesarios
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True          # Necesario para Auto Role y Logs de miembros
intents.moderation = True       # Necesario para Logs de baneos/kicks

bot = commands.Bot(command_prefix='!', intents=intents)

# ==========================================
# ⚙️ CONFIGURACIÓN DEL BOT
# ==========================================
# (Cuando el bot esté en el server, cambia estos nombres por los reales)
LOG_CHANNEL_NAME = "logs"    # Nombre del canal donde se mandarán los logs
AUTO_ROLE_NAME = "Members"       # Nombre del rol automático para nuevos usuarios

# Sistema Anti-SPAM (Máximo 10 mensajes en 3 segundos)
user_message_times = defaultdict(list)
SPAM_LIMIT = 10
SPAM_TIME_WINDOW = 3 # segundos

# ==========================================
# 🤖 EVENTOS DEL BOT
# ==========================================

@bot.event
async def on_ready():
    print(f'🤖 Bot iniciado correctamente como: {bot.user}')

# --- 1. AUTO ROLE & LOG DE BIENVENIDA ---
@bot.event
async def on_member_join(member):
    # Auto Role
    role = discord.utils.get(member.guild.roles, name=AUTO_ROLE_NAME)
    if role:
        await member.add_roles(role)
        print(f'✅ Rol {AUTO_ROLE_NAME} asignado a {member.name}')
    
    # Log de entrada
    log_channel = discord.utils.get(member.guild.text_channels, name=LOG_CHANNEL_NAME)
    if log_channel:
        embed = discord.Embed(
            title="📥 Nuevo miembro",
            description=f"{member.mention} (`{member.id}`) se ha unido al servidor.",
            color=discord.Color.green()
        )
        await log_channel.send(embed=embed)

# --- 2. LOG DE SALIDA ---
@bot.event
async def on_member_remove(member):
    log_channel = discord.utils.get(member.guild.text_channels, name=LOG_CHANNEL_NAME)
    if log_channel:
        embed = discord.Embed(
            title="📤 Miembro salió",
            description=f"**{member.name}** (`{member.id}`) ha dejado el servidor.",
            color=discord.Color.red()
        )
        await log_channel.send(embed=embed)

# --- 3. ANTI-SPAM & LOG DE BORRADO DE MENSAJES ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    current_time = time.time()
    user_id = message.author.id

    # Limpiar registros viejos del usuario
    user_message_times[user_id] = [t for t in user_message_times[user_id] if current_time - t < SPAM_TIME_WINDOW]
    user_message_times[user_id].append(current_time)

    # Verificar si superó el límite de SPAM
    if len(user_message_times[user_id]) > SPAM_LIMIT:
        await message.delete()
        await message.channel.send(f"⚠️ {message.author.mention}, no hagas spam.", delete_after=5)
        
        # Log de Anti-SPAM
        log_channel = discord.utils.get(message.guild.text_channels, name=LOG_CHANNEL_NAME)
        if log_channel:
            embed = discord.Embed(
                title="🚨 Anti-SPAM Activado",
                description=f"Se borró un mensaje por spam de {message.author.mention} en {message.channel.mention}.",
                color=discord.Color.orange()
            )
            await log_channel.send(embed=embed)
        return

    await bot.process_commands(message)

# --- 4. LOG DE MENSAJES EDITADOS ---
@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return

    log_channel = discord.utils.get(before.guild.text_channels, name=LOG_CHANNEL_NAME)
    if log_channel:
        embed = discord.Embed(
            title="✏️ Mensaje Editado",
            description=f"**Autor:** {before.author.mention}\n**Canal:** {before.channel.mention}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Antes", value=before.content or "Sin texto", inline=False)
        embed.add_field(name="Después", value=after.content or "Sin texto", inline=False)
        await log_channel.send(embed=embed)

# --- 5. LOG DE MENSAJES ELIMINADOS ---
@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return

    log_channel = discord.utils.get(message.guild.text_channels, name=LOG_CHANNEL_NAME)
    if log_channel:
        embed = discord.Embed(
            title="🗑️ Mensaje Eliminado",
            description=f"**Autor:** {message.author.mention}\n**Canal:** {message.channel.mention}\n**Contenido:** {message.content}",
            color=discord.Color.gold()
        )
        await log_channel.send(embed=embed)

# ==========================================
# 🚀 INICIO DEL BOT
# ==========================================
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ Esperando TOKEN en el archivo .env...")
