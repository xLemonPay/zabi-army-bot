import asyncio
import os
import re
import time
from datetime import timedelta
from typing import Optional

import aiohttp
import discord
from aiohttp import web
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
GUILD_ID = int(os.getenv("GUILD_ID", "0") or 0)
PORT = int(os.getenv("PORT", "8080") or 8080)

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID", "").strip()
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET", "").strip()
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL", "").strip().lstrip("@").lower()
TWITCH_CLIPS_POLL_SECONDS = max(60, int(os.getenv("TWITCH_CLIPS_POLL_SECONDS", "60") or 60))
TWITCH_CLIPS_LOOKBACK_MINUTES = max(30, int(os.getenv("TWITCH_CLIPS_LOOKBACK_MINUTES", "180") or 180))
TWITCH_ENABLED = bool(TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET and TWITCH_CHANNEL)

CAT_ENTRY = "╭・🚪 ANTES DE ENTRAR"
CAT_COMMUNITY = "╭・😈 ZABI ARMY"
CAT_GAMING = "╭・🎮 SE VINO EL VICIO"
CAT_VOICE = "╭・🔊 BAJÁ A HABLAR"
CAT_TICKETS = "╭・🎫 HABLÁ CON EL STAFF"

CH_START = "📍・por-donde-empiezo"
CH_RULES = "📜・las-reglas-del-juego"
CH_ANNOUNCEMENTS = "📣・zabi-dice"
CH_RESOURCES = "🔗・cosas-utiles"

CH_GENERAL = "💬・la-plaza"
CH_DELINQUENTS = "😈・los-delincuentes"
CH_LATE = "🌙・charlas-de-madrugada"
CH_MEDIA = "📸・pruebas-del-delito"
CH_MEMES = "😂・meme-del-dia"
CH_MUSIC = "🎧・la-rockola"
CH_CLIPS = "🎬・clips-de-zabi"
CH_SUGGESTIONS = "💡・tira-tu-idea"

CH_GAMING = "🎮・viciando"
CH_VALORANT = "🔫・ranked-y-lagrimas"
CH_LFG = "👥・busco-gente"
CH_COMPETITIVE = "🏆・competitivo"

VC_CONFESSIONAL = "😈・CONFESIONARIO"
VC_HELLFIRE = "🔥・hellfire-club"
VC_BASEMENT = "🕯️・el-sotano"
VC_INSOMNIA = "🌙・insomnio"
VC_CREATE = "➕・crear-sala"

CH_TICKET_PANEL = "🎫・abrir-ticket"

ALIASES = {
    CH_START: ["bienvenida-y-reglas", "bienvenida", "por-donde-empiezo"],
    CH_ANNOUNCEMENTS: ["anuncios", "zabi-dice"],
    CH_RESOURCES: ["recursos", "cosas-utiles"],
    CH_GENERAL: ["general", "la-plaza"],
    CH_DELINQUENTS: ["los-delincuentes"],
    CH_MUSIC: ["musiquita", "la-rockola"],
    CH_CLIPS: ["clips", "clips-de-zabi"],
    VC_CONFESSIONAL: ["CONFESIONARIO 😈", "CONFESIONARIO", "confesionario"],
    VC_HELLFIRE: ["hellfire club 😈", "hellfire club", "hellfire-club"],
    VC_BASEMENT: ["sotano", "sótano", "el-sotano"],
}

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

_http_session: Optional[aiohttp.ClientSession] = None
_twitch_token: Optional[str] = None
_twitch_token_expires_at = 0.0
_twitch_broadcaster_id: Optional[str] = None


def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9áéíóúüñ]+", "", value.casefold())


def is_staff(member: discord.Member) -> bool:
    perms = member.guild_permissions
    return perms.administrator or perms.manage_guild or perms.manage_channels or perms.manage_messages


def find_category(guild: discord.Guild, name: str) -> Optional[discord.CategoryChannel]:
    return discord.utils.get(guild.categories, name=name)


def find_text(guild: discord.Guild, name: str) -> Optional[discord.TextChannel]:
    return discord.utils.get(guild.text_channels, name=name)


def find_voice(guild: discord.Guild, name: str) -> Optional[discord.VoiceChannel]:
    return discord.utils.get(guild.voice_channels, name=name)


def find_alias_text(guild: discord.Guild, target: str) -> Optional[discord.TextChannel]:
    direct = find_text(guild, target)
    if direct:
        return direct
    wanted = {normalized_name(alias) for alias in ALIASES.get(target, [])}
    for channel in guild.text_channels:
        if normalized_name(channel.name) in wanted:
            return channel
    return None


def find_alias_voice(guild: discord.Guild, target: str) -> Optional[discord.VoiceChannel]:
    direct = find_voice(guild, target)
    if direct:
        return direct
    wanted = {normalized_name(alias) for alias in ALIASES.get(target, [])}
    for channel in guild.voice_channels:
        if normalized_name(channel.name) in wanted:
            return channel
    return None


async def ensure_category(guild: discord.Guild, name: str) -> discord.CategoryChannel:
    category = find_category(guild, name)
    if category is None:
        category = await guild.create_category(name, reason="Instalación Zabi Army Bot")
    return category


async def ensure_text(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    name: str,
    *,
    topic: Optional[str] = None,
    readonly: bool = False,
) -> discord.TextChannel:
    channel = find_alias_text(guild, name)
    if channel is None:
        channel = await guild.create_text_channel(name, category=category, topic=topic, reason="Instalación Zabi Army Bot")
    else:
        edits = {}
        if channel.name != name:
            edits["name"] = name
        if channel.category_id != category.id:
            edits["category"] = category
        if topic is not None and channel.topic != topic:
            edits["topic"] = topic
        if edits:
            await channel.edit(**edits, reason="Migración Zabi Army Bot")

    if readonly:
        everyone = guild.default_role
        overwrite = channel.overwrites_for(everyone)
        overwrite.view_channel = True
        overwrite.send_messages = False
        overwrite.add_reactions = True
        await channel.set_permissions(everyone, overwrite=overwrite, reason="Canal de solo lectura")
        if guild.me:
            mine = channel.overwrites_for(guild.me)
            mine.view_channel = True
            mine.send_messages = True
            mine.embed_links = True
            mine.attach_files = True
            await channel.set_permissions(guild.me, overwrite=mine, reason="Permisos del bot")
    return channel


async def ensure_voice(guild: discord.Guild, category: discord.CategoryChannel, name: str) -> discord.VoiceChannel:
    channel = find_alias_voice(guild, name)
    if channel is None:
        channel = await guild.create_voice_channel(name, category=category, reason="Instalación Zabi Army Bot")
    else:
        edits = {}
        if channel.name != name:
            edits["name"] = name
        if channel.category_id != category.id:
            edits["category"] = category
        if edits:
            await channel.edit(**edits, reason="Migración Zabi Army Bot")
    return channel


async def safe_send_or_edit_panel(
    channel: discord.TextChannel,
    *,
    title: str,
    description: str,
    view: discord.ui.View,
) -> discord.Message:
    async for message in channel.history(limit=50):
        if message.author == channel.guild.me and message.embeds and message.embeds[0].title == title:
            embed = discord.Embed(title=title, description=description, colour=discord.Colour.purple())
            await message.edit(embed=embed, view=view)
            return message
    embed = discord.Embed(title=title, description=description, colour=discord.Colour.purple())
    return await channel.send(embed=embed, view=view)


class SuggestionModal(discord.ui.Modal, title="Tirá tu idea"):
    idea = discord.ui.TextInput(
        label="Tu sugerencia",
        placeholder="Contanos qué te gustaría agregar o cambiar...",
        style=discord.TextStyle.paragraph,
        max_length=1500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message("No pude publicar la sugerencia.", ephemeral=True)

        embed = discord.Embed(
            title="💡 Nueva idea para Zabi Army",
            description=self.idea.value.strip(),
            colour=discord.Colour.gold(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Estado", value="🟡 Pendiente", inline=True)
        embed.add_field(name="Enviada por", value=interaction.user.mention, inline=True)
        embed.set_footer(text=f"Autor ID: {interaction.user.id}")
        await interaction.response.defer(ephemeral=True)
        message = await interaction.channel.send(embed=embed)
        await message.add_reaction("👍")
        await message.add_reaction("👎")
        await interaction.followup.send("✅ Tu sugerencia fue publicada.", ephemeral=True)


class SuggestionPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Enviar sugerencia",
        emoji="💡",
        style=discord.ButtonStyle.primary,
        custom_id="zabi:suggestion:new",
    )
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SuggestionModal())


@app_commands.choices(
    estado=[
        app_commands.Choice(name="Pendiente", value="🟡 Pendiente"),
        app_commands.Choice(name="En revisión", value="🔵 En revisión"),
        app_commands.Choice(name="Aceptada", value="🟢 Aceptada"),
        app_commands.Choice(name="Rechazada", value="🔴 Rechazada"),
    ]
)
@bot.tree.command(name="sugerencia-estado", description="Cambia el estado de una sugerencia.")
@app_commands.guild_only()
async def suggestion_status(interaction: discord.Interaction, mensaje_id: str, estado: app_commands.Choice[str]):
    if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
        return await interaction.response.send_message("Solo el staff puede cambiar estados.", ephemeral=True)
    channel = find_text(interaction.guild, CH_SUGGESTIONS) if interaction.guild else None
    if channel is None:
        return await interaction.response.send_message("No encuentro el canal de sugerencias.", ephemeral=True)
    try:
        message = await channel.fetch_message(int(mensaje_id))
    except (ValueError, discord.NotFound):
        return await interaction.response.send_message("No encontré ese mensaje.", ephemeral=True)
    if not message.embeds:
        return await interaction.response.send_message("Ese mensaje no es una sugerencia válida.", ephemeral=True)
    embed = discord.Embed.from_dict(message.embeds[0].to_dict())
    if embed.fields:
        embed.set_field_at(0, name="Estado", value=estado.value, inline=True)
    else:
        embed.add_field(name="Estado", value=estado.value, inline=True)
    await message.edit(embed=embed)
    await interaction.response.send_message(f"✅ Estado actualizado a **{estado.name}**.", ephemeral=True)


def ticket_staff_roles(guild: discord.Guild) -> list[discord.Role]:
    return [
        role
        for role in guild.roles
        if role != guild.default_role
        and (role.permissions.administrator or role.permissions.manage_guild or role.permissions.manage_channels or role.permissions.manage_messages)
    ]


def ticket_owner_id(channel: discord.TextChannel) -> Optional[int]:
    if not channel.topic:
        return None
    match = re.search(r"ticket_owner:(\d+)", channel.topic)
    return int(match.group(1)) if match else None


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cerrar ticket", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="zabi:ticket:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
            return
        owner_id = ticket_owner_id(interaction.channel)
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if member is None or (member.id != owner_id and not is_staff(member)):
            return await interaction.response.send_message("Solo quien abrió el ticket o el staff puede cerrarlo.", ephemeral=True)
        await interaction.response.send_message("🔒 Cerrando ticket en 3 segundos...", ephemeral=True)
        await asyncio.sleep(3)
        try:
            await interaction.channel.delete(reason=f"Ticket cerrado por {interaction.user}")
        except discord.NotFound:
            pass


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir ticket", emoji="🎫", style=discord.ButtonStyle.success, custom_id="zabi:ticket:open")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return
        guild = interaction.guild
        category = find_category(guild, CAT_TICKETS)
        if category is None:
            return await interaction.response.send_message("No encuentro la categoría de tickets.", ephemeral=True)

        for channel in category.text_channels:
            if ticket_owner_id(channel) == interaction.user.id:
                return await interaction.response.send_message(f"Ya tenés un ticket abierto: {channel.mention}", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
        }
        if guild.me:
            overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)
        for role in ticket_staff_roles(guild):
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        safe_name = re.sub(r"[^a-z0-9-]", "", interaction.user.name.lower().replace(" ", "-"))[:40] or str(interaction.user.id)
        channel = await guild.create_text_channel(
            f"ticket-{safe_name}",
            category=category,
            overwrites=overwrites,
            topic=f"ticket_owner:{interaction.user.id}",
            reason=f"Ticket abierto por {interaction.user}",
        )
        embed = discord.Embed(
            title="🎫 Ticket abierto",
            description=(
                f"Hola {interaction.user.mention}. Contanos qué necesitás y el staff te responde por acá.\n\n"
                "Cuando terminen, usen **Cerrar ticket**."
            ),
            colour=discord.Colour.purple(),
        )
        await channel.send(content=interaction.user.mention, embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Ticket creado: {channel.mention}", ephemeral=True)


async def twitch_session() -> aiohttp.ClientSession:
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))
    return _http_session


async def get_twitch_token(force: bool = False) -> str:
    global _twitch_token, _twitch_token_expires_at
    if not TWITCH_ENABLED:
        raise RuntimeError("Twitch no está configurado")
    now = time.time()
    if not force and _twitch_token and now < _twitch_token_expires_at - 60:
        return _twitch_token
    session = await twitch_session()
    async with session.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials",
        },
    ) as response:
        data = await response.json(content_type=None)
        if response.status != 200:
            raise RuntimeError(f"Twitch OAuth HTTP {response.status}: {data}")
    _twitch_token = data["access_token"]
    _twitch_token_expires_at = now + int(data.get("expires_in", 3600))
    return _twitch_token


async def twitch_get(path: str, params: dict) -> dict:
    token = await get_twitch_token()
    session = await twitch_session()
    for attempt in range(2):
        async with session.get(
            f"https://api.twitch.tv/helix/{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}", "Client-Id": TWITCH_CLIENT_ID},
        ) as response:
            data = await response.json(content_type=None)
            if response.status == 401 and attempt == 0:
                token = await get_twitch_token(force=True)
                continue
            if response.status != 200:
                raise RuntimeError(f"Twitch {path} HTTP {response.status}: {data}")
            return data
    raise RuntimeError("No se pudo autenticar con Twitch")


async def get_broadcaster_id() -> str:
    global _twitch_broadcaster_id
    if _twitch_broadcaster_id:
        return _twitch_broadcaster_id
    data = await twitch_get("users", {"login": TWITCH_CHANNEL})
    users = data.get("data") or []
    if not users:
        raise RuntimeError(f"No existe el canal de Twitch @{TWITCH_CHANNEL}")
    _twitch_broadcaster_id = str(users[0]["id"])
    return _twitch_broadcaster_id


async def fetch_recent_clips() -> list[dict]:
    broadcaster_id = await get_broadcaster_id()
    started = discord.utils.utcnow() - timedelta(minutes=TWITCH_CLIPS_LOOKBACK_MINUTES)
    params = {
        "broadcaster_id": broadcaster_id,
        "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "first": "100",
    }
    clips: list[dict] = []
    cursor = None
    for _ in range(3):
        if cursor:
            params["after"] = cursor
        data = await twitch_get("clips", params)
        clips.extend(data.get("data") or [])
        cursor = (data.get("pagination") or {}).get("cursor")
        if not cursor:
            break
    unique = {str(clip.get("id")): clip for clip in clips if clip.get("id")}
    return sorted(unique.values(), key=lambda c: c.get("created_at") or "")


async def posted_clip_ids(channel: discord.TextChannel) -> set[str]:
    ids: set[str] = set()
    async for message in channel.history(limit=500):
        if message.author != channel.guild.me:
            continue
        for embed in message.embeds:
            footer = embed.footer.text if embed.footer else ""
            if footer.startswith("Twitch clip ID: "):
                ids.add(footer.removeprefix("Twitch clip ID: ").strip())
    return ids


def clip_embed(clip: dict) -> discord.Embed:
    url = clip.get("url") or f"https://www.twitch.tv/{TWITCH_CHANNEL}"
    embed = discord.Embed(
        title=f"🎬 Nuevo clip de {clip.get('broadcaster_name') or TWITCH_CHANNEL}",
        url=url,
        description=f"**{clip.get('title') or 'Nuevo clip'}**",
        colour=discord.Colour.purple(),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="✂️ Creado por", value=clip.get("creator_name") or "Desconocido", inline=True)
    embed.add_field(name="👀 Vistas", value=str(clip.get("view_count") or 0), inline=True)
    if clip.get("thumbnail_url"):
        embed.set_image(url=clip["thumbnail_url"])
    embed.set_footer(text=f"Twitch clip ID: {clip.get('id')}")
    return embed


def clip_view(clip: dict) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Ver clip", emoji="🟣", style=discord.ButtonStyle.link, url=clip.get("url") or f"https://www.twitch.tv/{TWITCH_CHANNEL}"))
    return view


@tasks.loop(seconds=TWITCH_CLIPS_POLL_SECONDS)
async def clips_watch():
    if not TWITCH_ENABLED or not GUILD_ID:
        return
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        return
    channel = find_text(guild, CH_CLIPS)
    if channel is None:
        return
    try:
        clips = await fetch_recent_clips()
        already = await posted_clip_ids(channel)
        pending = [clip for clip in clips if str(clip.get("id")) not in already]
        for clip in pending[-10:]:
            await channel.send(embed=clip_embed(clip), view=clip_view(clip))
        if pending:
            print(f"🎬 Clips publicados: {min(len(pending), 10)}")
    except Exception as exc:
        print(f"⚠️ Clips Twitch: {type(exc).__name__}: {exc}")


@clips_watch.before_loop
async def before_clips_watch():
    await bot.wait_until_ready()


async def install_server(guild: discord.Guild) -> None:
    entry = await ensure_category(guild, CAT_ENTRY)
    community = await ensure_category(guild, CAT_COMMUNITY)
    gaming = await ensure_category(guild, CAT_GAMING)
    voice = await ensure_category(guild, CAT_VOICE)
    tickets = await ensure_category(guild, CAT_TICKETS)

    await ensure_text(guild, entry, CH_START, topic="Empezá por acá: bienvenida e información principal.")
    await ensure_text(guild, entry, CH_RULES, topic="Reglas de convivencia de Zabi Army.", readonly=True)
    await ensure_text(guild, entry, CH_ANNOUNCEMENTS, topic="Anuncios oficiales de Zabi Army.", readonly=True)
    await ensure_text(guild, entry, CH_RESOURCES, topic="Links y recursos útiles.", readonly=True)

    await ensure_text(guild, community, CH_GENERAL, topic="La charla principal de Zabi Army.")
    await ensure_text(guild, community, CH_DELINQUENTS, topic="El rincón de los delincuentes 😈")
    await ensure_text(guild, community, CH_LATE, topic="Charlas para cuando nadie quiere dormir.")
    await ensure_text(guild, community, CH_MEDIA, topic="Fotos, capturas y pruebas del delito.")
    await ensure_text(guild, community, CH_MEMES, topic="Memes y caos controlado.")
    await ensure_text(guild, community, CH_MUSIC, topic="Pasá temas y playlists.")
    clips = await ensure_text(guild, community, CH_CLIPS, topic="Clips nuevos de Zabi publicados automáticamente.", readonly=True)
    suggestions = await ensure_text(guild, community, CH_SUGGESTIONS, topic="Ideas y sugerencias de la comunidad.", readonly=True)

    await ensure_text(guild, gaming, CH_GAMING, topic="Gaming general.")
    await ensure_text(guild, gaming, CH_VALORANT, topic="Rankeds, Valorant y sufrimiento competitivo.")
    await ensure_text(guild, gaming, CH_LFG, topic="Buscá gente para jugar.")
    await ensure_text(guild, gaming, CH_COMPETITIVE, topic="Competitivo, customs y torneos.")

    await ensure_voice(guild, voice, VC_CONFESSIONAL)
    await ensure_voice(guild, voice, VC_HELLFIRE)
    await ensure_voice(guild, voice, VC_BASEMENT)
    await ensure_voice(guild, voice, VC_INSOMNIA)
    await ensure_voice(guild, voice, VC_CREATE)

    ticket_panel = await ensure_text(guild, tickets, CH_TICKET_PANEL, topic="Abrí un ticket privado con el staff.", readonly=True)

    await safe_send_or_edit_panel(
        suggestions,
        title="💡 Tirate una idea",
        description="¿Se te ocurrió algo para mejorar Zabi Army? Tocá el botón y mandalo. La comunidad puede votar con 👍 y 👎.",
        view=SuggestionPanelView(),
    )
    await safe_send_or_edit_panel(
        ticket_panel,
        title="🎫 Hablá con el staff",
        description="¿Necesitás ayuda o querés hablar algo en privado? Abrí un ticket y se crea un canal que solo vos y el staff pueden ver.",
        view=TicketPanelView(),
    )

    # Silencia permisos de escritura de miembros en clips; el bot conserva acceso.
    if guild.me:
        clip_ow = clips.overwrites_for(guild.me)
        clip_ow.view_channel = True
        clip_ow.send_messages = True
        clip_ow.embed_links = True
        await clips.set_permissions(guild.me, overwrite=clip_ow, reason="Publicación automática de clips")


@bot.tree.command(name="setup", description="Instala o actualiza la estructura de Zabi Army sin borrar canales.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        return
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Necesitás Administrador para usar este comando.", ephemeral=True)
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await install_server(interaction.guild)
        await interaction.followup.send(
            "✅ **Zabi Army Bot instalado.**\n"
            "No borré canales: reutilicé/migré los conocidos y creé solo lo que faltaba.\n"
            "🎬 Clips • 💡 Sugerencias • 🎫 Tickets listos.",
            ephemeral=True,
        )
    except discord.Forbidden:
        await interaction.followup.send("❌ Me faltan permisos. Revisá **Gestionar canales** y **Gestionar mensajes**.", ephemeral=True)
    except Exception as exc:
        await interaction.followup.send(f"❌ Error: `{type(exc).__name__}: {str(exc)[:600]}`", ephemeral=True)
        raise


@bot.tree.command(name="bot-estado", description="Muestra el estado básico del Zabi Army Bot.")
@app_commands.guild_only()
async def bot_status(interaction: discord.Interaction):
    twitch = f"✅ @{TWITCH_CHANNEL}" if TWITCH_ENABLED else "❌ sin configurar"
    await interaction.response.send_message(
        f"🤖 **Zabi Army Bot**\n🎬 Twitch: {twitch}\n💡 Sugerencias: ✅\n🎫 Tickets: ✅",
        ephemeral=True,
    )


@bot.tree.command(name="clips-revisar", description="Revisa Twitch ahora mismo y publica clips pendientes.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def clips_check(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
        return await interaction.response.send_message("Solo el staff puede usar esto.", ephemeral=True)
    if not TWITCH_ENABLED:
        return await interaction.response.send_message("Twitch todavía no está configurado.", ephemeral=True)
    channel = find_text(interaction.guild, CH_CLIPS) if interaction.guild else None
    if channel is None:
        return await interaction.response.send_message("No encuentro el canal de clips.", ephemeral=True)
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        clips = await fetch_recent_clips()
        already = await posted_clip_ids(channel)
        pending = [clip for clip in clips if str(clip.get("id")) not in already]
        for clip in pending[-10:]:
            await channel.send(embed=clip_embed(clip), view=clip_view(clip))
        await interaction.followup.send(f"✅ Revisión terminada. Clips nuevos publicados: **{min(len(pending), 10)}**.", ephemeral=True)
    except Exception as exc:
        await interaction.followup.send(f"❌ Twitch: `{type(exc).__name__}: {str(exc)[:600]}`", ephemeral=True)


async def health(_request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "bot": "zabi-army-bot", "discord_ready": bot.is_ready()})


async def start_health_server() -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Health server activo en puerto {PORT}")
    return runner


@bot.event
async def on_ready():
    if bot.user is None:
        return
    print(f"✅ Conectado como {bot.user} ({bot.user.id})")
    await bot.change_presence(activity=discord.Game(name="Zabi Army 😈"))
    if not getattr(bot, "_zabi_synced", False):
        try:
            if GUILD_ID:
                guild_obj = discord.Object(id=GUILD_ID)
                bot.tree.copy_global_to(guild=guild_obj)
                synced = await bot.tree.sync(guild=guild_obj)
                print(f"✅ {len(synced)} comandos sincronizados en el servidor")
            else:
                synced = await bot.tree.sync()
                print(f"✅ {len(synced)} comandos globales sincronizados")
            bot._zabi_synced = True
        except Exception as exc:
            print(f"⚠️ Error sincronizando comandos: {exc}")
    if TWITCH_ENABLED and not clips_watch.is_running():
        clips_watch.start()
        print(f"🎬 Twitch clips activo: @{TWITCH_CHANNEL} cada {TWITCH_CLIPS_POLL_SECONDS}s")


async def main():
    if not TOKEN:
        raise RuntimeError("Falta DISCORD_TOKEN")
    bot.add_view(SuggestionPanelView())
    bot.add_view(TicketPanelView())
    bot.add_view(CloseTicketView())
    runner = await start_health_server()
    try:
        await bot.start(TOKEN)
    finally:
        if clips_watch.is_running():
            clips_watch.cancel()
        if _http_session and not _http_session.closed:
            await _http_session.close()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
