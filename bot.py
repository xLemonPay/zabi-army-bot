import asyncio
import io
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
ENABLE_MESSAGE_LOGS = os.getenv("ENABLE_MESSAGE_LOGS", "false").strip().lower() in {"1", "true", "yes", "on"}

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID", "").strip()
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET", "").strip()
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL", "").strip().lstrip("@").lower()
STREAMER_DISCORD_ID = int(os.getenv("STREAMER_DISCORD_ID", "0") or 0)
TWITCH_POLL_SECONDS = max(30, int(os.getenv("TWITCH_POLL_SECONDS", "60") or 60))
TWITCH_OFFLINE_DELETE_DELAY = max(0, int(os.getenv("TWITCH_OFFLINE_DELETE_DELAY", "300") or 300))
TWITCH_CLIPS_POLL_SECONDS = max(60, int(os.getenv("TWITCH_CLIPS_POLL_SECONDS", "60") or 60))
TWITCH_CLIPS_LOOKBACK_MINUTES = max(30, int(os.getenv("TWITCH_CLIPS_LOOKBACK_MINUTES", "180") or 180))
TWITCH_ENABLED = bool(TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET and TWITCH_CHANNEL)

# ──────────────────────────────────────────────────────────────────────────────
# IDENTIDAD / CANALES — NO se renombran canales existentes.
# Los aliases permiten reutilizar los canales reales de Zabi sin cambiarles el nombre.
# ──────────────────────────────────────────────────────────────────────────────

CAT_ENTRY = "╭・🚪 ANTES DE ENTRAR"
CAT_COMMUNITY = "╭・😈 ZABI ARMY"
CAT_GAMING = "╭・🎮 SE VINO EL VICIO"
CAT_VOICE = "╭・🔊 BAJÁ A HABLAR"
CAT_TICKETS = "╭・🎫 HABLÁ CON EL STAFF"
CAT_STAFF = "╭・🛡️ LA OFICINA"

CH_VERIFY = "✅・verificate"
CH_RULES = "📜・las-reglas-del-juego"
CH_ANNOUNCEMENTS = "📣・zabi-dice"
CH_RESOURCES = "🔗・cosas-utiles"
CH_ROLES = "🎭・elegi-tus-roles"

CH_GENERAL = "💬・la-plaza"
CH_WELCOME = "👋・nuevos-delincuentes"
CH_DELINQUENTS = "😈・los-delincuentes"
CH_LATE = "🌙・charlas-de-madrugada"
CH_MEDIA = "📸・pruebas-del-delito"
CH_MEMES = "😂・meme-del-dia"
CH_MUSIC = "🎵・musiquita"
CH_CLIPS = "🎬・clips-de-zabi"
CH_SUGGESTIONS = "💡・tira-tu-idea"
CH_LIVE = "🔴・zabi-en-vivo"

CH_GAMING = "🎮・viciando"
CH_VALORANT = "🔫・ranked-y-lagrimas"
CH_LFG = "👥・busco-gente"
CH_COMPETITIVE = "🏆・competitivo"

VC_CONFESSIONAL = "👹・CONFESIONARIO"
VC_HELLFIRE = "👹・hellfire-club"
VC_BASEMENT = "🕯️・el-sotano"
VC_INSOMNIA = "🌙・insomnio"
VC_CREATE = "➕・crear-sala"
VC_LIVE = "🔴・EN DIRECTO | RESPETO"
TEMP_VC_PREFIX = "🎧・Sala de "

CH_TICKET_PANEL = "🎫・abrir-ticket"
CH_STAFF = "🛡️・la-oficina"
CH_REPORTS = "🚨・casos-abiertos"
CH_LOGS = "📜・historial"

TEXT_ALIASES = {
    CH_VERIFY: ["bienvenida-y-reglas", "bienvenida", "verificate", "verificacion", "verificación"],
    CH_RULES: ["reglas", "rules"],
    CH_ANNOUNCEMENTS: ["anuncios", "zabi-dice"],
    CH_RESOURCES: ["recursos", "cosas-utiles"],
    CH_ROLES: ["roles", "elegi-tus-roles"],
    CH_GENERAL: ["general", "la-plaza"],
    CH_WELCOME: ["bienvenidas", "nuevos-delincuentes"],
    CH_DELINQUENTS: ["los-delincuentes"],
    CH_LATE: ["charlas-de-madrugada"],
    CH_MEDIA: ["multimedia", "pruebas-del-delito"],
    CH_MEMES: ["memes", "meme-del-dia"],
    CH_MUSIC: ["musiquita", "la-rockola"],
    CH_CLIPS: ["clips", "clips-de-zabi"],
    CH_SUGGESTIONS: ["sugerencias", "tira-tu-idea"],
    CH_GAMING: ["gaming", "viciando"],
    CH_VALORANT: ["valorant", "ranked-y-lagrimas"],
    CH_LFG: ["busco-grupo", "busco-gente"],
    CH_COMPETITIVE: ["competitivo"],
    CH_TICKET_PANEL: ["abrir-ticket"],
    CH_STAFF: ["staff", "la-oficina"],
    CH_REPORTS: ["reportes", "casos-abiertos"],
    CH_LOGS: ["logs", "historial"],
}

VOICE_ALIASES = {
    VC_CONFESSIONAL: ["CONFESIONARIO 😈", "CONFESIONARIO 👹", "CONFESIONARIO", "confesionario"],
    VC_HELLFIRE: ["hellfire club 😈", "hellfire club 👹", "hellfire club", "hellfire-club"],
    VC_BASEMENT: ["sotano", "sótano", "el-sotano"],
    VC_INSOMNIA: ["insomnio"],
    VC_CREATE: ["Crear sala", "crear-sala"],
}

# ──────────────────────────────────────────────────────────────────────────────
# ROLES — misma base del bot de s0ftbl4de.
# ──────────────────────────────────────────────────────────────────────────────

ROLE_MEMBER = "✅・Miembro"
ROLE_OWNER = "👑・Owner"
ROLE_COOWNER = "💎・Co-Owner"
ROLE_ADMIN = "🛡️・Admin"
ROLE_MOD = "🔨・Moderador"
ROLE_STREAMER = "🎥・Streamer"
ROLE_SUB = "💜・Subscriber"
ROLE_VIP = "⭐・VIP"
ROLE_LIVE = "🔴・EN DIRECTO"
ROLE_LIVE_NOTIFY = "🔔・Avisos de directo"
ROLE_EVENT_NOTIFY = "🎉・Avisos de eventos"

ROLE_GAME_VALORANT = "🔫・Valorant"
ROLE_GAME_MINECRAFT = "⛏️・Minecraft"
ROLE_GAME_OTHER = "🎮・Otros juegos"
ROLE_PLATFORM_PC = "🖥️・PC"
ROLE_PLATFORM_CONSOLE = "🎮・Consola"
ROLE_PLATFORM_MOBILE = "📱・Mobile"

AGE_ROLES = [
    "🧒・Menor de 18",
    "🎂・18-25",
    "🧑・26+",
]

COUNTRIES = [
    "🇵🇾・Paraguay",
    "🇦🇷・Argentina",
    "🇧🇷・Brasil",
    "🇺🇾・Uruguay",
    "🇨🇱・Chile",
    "🇧🇴・Bolivia",
    "🇵🇪・Perú",
    "🇨🇴・Colombia",
    "🇻🇪・Venezuela",
    "🇪🇨・Ecuador",
    "🇲🇽・México",
    "🇪🇸・España",
    "🌎・Otro",
]

VALORANT_RANKS = [
    "⚫・Sin rango",
    "⬛・Hierro",
    "🟫・Bronce",
    "⬜・Plata",
    "🟨・Oro",
    "🟩・Platino",
    "💎・Diamante",
    "🟪・Ascendente",
    "🟥・Inmortal",
    "🌟・Radiante",
]

LEGACY_ROLE_ALIASES = {
    ROLE_STREAMER: ["🎥・Zabi"],
    ROLE_VIP: ["💎・VIP"],
    ROLE_LIVE_NOTIFY: ["🔔・Avisos de Zabi"],
}

GUIDE_PREFIX = "📌 Guía — "
SUGGESTION_PANEL_TITLE = "💡 Buzón de sugerencias"
SUGGESTION_FOOTER_PREFIX = "zabi_suggestion|"

# ──────────────────────────────────────────────────────────────────────────────
# BOT / INTENTS
# ──────────────────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.messages = True
intents.reactions = True
intents.message_content = ENABLE_MESSAGE_LOGS

bot = commands.Bot(command_prefix="!", intents=intents)

_http_session: Optional[aiohttp.ClientSession] = None
_twitch_token: Optional[str] = None
_twitch_token_expires_at = 0.0
_twitch_broadcaster_id: Optional[str] = None
_twitch_was_live: Optional[bool] = None
_twitch_last_stream_id: Optional[str] = None
_twitch_delete_task: Optional[asyncio.Task] = None
_twitch_test_mode = False

# ──────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ──────────────────────────────────────────────────────────────────────────────

def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9áéíóúüñ]+", "", value.casefold())


def _name_matches(value: str, target: str, aliases: list[str]) -> bool:
    wanted = {normalized_name(target), *(normalized_name(x) for x in aliases)}
    return normalized_name(value) in wanted


def find_role(guild: discord.Guild, name: str) -> Optional[discord.Role]:
    direct = discord.utils.get(guild.roles, name=name)
    if direct:
        return direct
    for alias in LEGACY_ROLE_ALIASES.get(name, []):
        role = discord.utils.get(guild.roles, name=alias)
        if role:
            return role
    return None


def find_category(guild: discord.Guild, name: str) -> Optional[discord.CategoryChannel]:
    return discord.utils.get(guild.categories, name=name)


def find_text(guild: discord.Guild, name: str) -> Optional[discord.TextChannel]:
    direct = discord.utils.get(guild.text_channels, name=name)
    if direct:
        return direct
    aliases = TEXT_ALIASES.get(name, [])
    for channel in guild.text_channels:
        if _name_matches(channel.name, name, aliases):
            return channel
    return None


def find_voice(guild: discord.Guild, name: str) -> Optional[discord.VoiceChannel]:
    direct = discord.utils.get(guild.voice_channels, name=name)
    if direct:
        return direct
    aliases = VOICE_ALIASES.get(name, [])
    for channel in guild.voice_channels:
        if _name_matches(channel.name, name, aliases):
            return channel
    return None


def safe_text(text: str, limit: int = 1000) -> str:
    if not text:
        return "*(sin texto)*"
    text = discord.utils.escape_mentions(text)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def is_staff(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    staff_names = {ROLE_OWNER, ROLE_COOWNER, ROLE_ADMIN, ROLE_MOD, ROLE_STREAMER}
    return any(role.name in staff_names or role.name in LEGACY_ROLE_ALIASES.get(ROLE_STREAMER, []) for role in member.roles)


def staff_roles(guild: discord.Guild) -> list[discord.Role]:
    found = []
    for name in (ROLE_OWNER, ROLE_COOWNER, ROLE_ADMIN, ROLE_MOD, ROLE_STREAMER):
        role = find_role(guild, name)
        if role and role not in found:
            found.append(role)
    return found


async def ensure_role(
    guild: discord.Guild,
    name: str,
    permissions: discord.Permissions,
    colour: int = 0x99AAB5,
    hoist: bool = False,
) -> discord.Role:
    role = find_role(guild, name)
    wanted_colour = discord.Colour(colour)
    if role is None:
        return await guild.create_role(
            name=name,
            permissions=permissions,
            colour=wanted_colour,
            hoist=hoist,
            mentionable=False,
            reason="Setup automático Zabi Army",
        )

    me = guild.me
    if me is not None and role >= me.top_role:
        return role

    edits = {}
    if role.name != name:
        edits["name"] = name
    if role.permissions != permissions:
        edits["permissions"] = permissions
    if role.colour != wanted_colour:
        edits["colour"] = wanted_colour
    if role.hoist != hoist:
        edits["hoist"] = hoist
    if role.mentionable:
        edits["mentionable"] = False
    if edits:
        await role.edit(**edits, reason="Actualizar roles Zabi Army")
    return role


async def ensure_roles(guild: discord.Guild) -> dict[str, discord.Role]:
    owner_perms = discord.Permissions(administrator=True)
    coowner_perms = discord.Permissions(administrator=True)

    admin_perms = discord.Permissions.none()
    for perm in (
        "view_audit_log", "manage_guild", "manage_roles", "manage_channels",
        "kick_members", "ban_members", "moderate_members", "manage_nicknames",
        "manage_messages", "manage_threads", "manage_events", "mute_members",
        "deafen_members", "move_members",
    ):
        setattr(admin_perms, perm, True)

    mod_perms = discord.Permissions.none()
    for perm in (
        "view_audit_log", "kick_members", "ban_members", "moderate_members",
        "manage_nicknames", "manage_messages", "manage_threads",
        "mute_members", "deafen_members", "move_members",
    ):
        setattr(mod_perms, perm, True)

    none = discord.Permissions.none()
    roles: dict[str, discord.Role] = {}
    roles[ROLE_OWNER] = await ensure_role(guild, ROLE_OWNER, owner_perms, 0x000000, False)
    roles[ROLE_COOWNER] = await ensure_role(guild, ROLE_COOWNER, coowner_perms, 0xE67E22, True)
    roles[ROLE_ADMIN] = await ensure_role(guild, ROLE_ADMIN, admin_perms, 0xE74C3C, True)
    roles[ROLE_MOD] = await ensure_role(guild, ROLE_MOD, mod_perms, 0x3498DB, True)
    roles[ROLE_STREAMER] = await ensure_role(guild, ROLE_STREAMER, none, 0xEB459E, True)
    roles[ROLE_SUB] = await ensure_role(guild, ROLE_SUB, none, 0x9B59B6, False)
    roles[ROLE_VIP] = await ensure_role(guild, ROLE_VIP, none, 0xFEE75C, False)
    roles[ROLE_MEMBER] = await ensure_role(guild, ROLE_MEMBER, none, 0x57F287, False)
    roles[ROLE_LIVE] = await ensure_role(guild, ROLE_LIVE, none, 0xED4245, True)
    roles[ROLE_LIVE_NOTIFY] = await ensure_role(guild, ROLE_LIVE_NOTIFY, none, 0x9146FF, False)
    roles[ROLE_EVENT_NOTIFY] = await ensure_role(guild, ROLE_EVENT_NOTIFY, none, 0xF1C40F, False)

    for role_name in (
        ROLE_GAME_VALORANT, ROLE_GAME_MINECRAFT, ROLE_GAME_OTHER,
        ROLE_PLATFORM_PC, ROLE_PLATFORM_CONSOLE, ROLE_PLATFORM_MOBILE,
    ):
        roles[role_name] = await ensure_role(guild, role_name, none, 0x99AAB5, False)

    for role_name in AGE_ROLES:
        roles[role_name] = await ensure_role(guild, role_name, none, 0x99AAB5, False)

    for role_name in COUNTRIES:
        roles[role_name] = await ensure_role(guild, role_name, none, 0x99AAB5, False)

    rank_colours = {
        "⚫・Sin rango": 0x5865F2,
        "⬛・Hierro": 0x5D5D5D,
        "🟫・Bronce": 0xA97142,
        "⬜・Plata": 0xB7C9D3,
        "🟨・Oro": 0xE5B73B,
        "🟩・Platino": 0x44C7B1,
        "💎・Diamante": 0x8FA8FF,
        "🟪・Ascendente": 0x4DD39C,
        "🟥・Inmortal": 0xC94B68,
        "🌟・Radiante": 0xFFF0A6,
    }
    for role_name in VALORANT_RANKS:
        roles[role_name] = await ensure_role(guild, role_name, none, rank_colours[role_name], False)
    return roles


async def ensure_role_order(guild: discord.Guild) -> None:
    me = guild.me
    if me is None:
        return
    ordered = [
        ROLE_OWNER, ROLE_LIVE, ROLE_STREAMER, ROLE_COOWNER, ROLE_ADMIN, ROLE_MOD,
        ROLE_SUB, ROLE_VIP, ROLE_MEMBER, ROLE_LIVE_NOTIFY, ROLE_EVENT_NOTIFY,
    ]
    target = me.top_role.position - 1
    try:
        for name in ordered:
            role = find_role(guild, name)
            if role is None or role >= me.top_role or target <= 0:
                continue
            if role.position != target:
                await role.edit(position=target, reason="Jerarquía Zabi Army")
            target -= 1
    except (discord.Forbidden, discord.HTTPException):
        pass


def verification_overwrites(guild: discord.Guild) -> dict:
    ow = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True, send_messages=False, add_reactions=False, read_message_history=True
        )
    }
    for role in staff_roles(guild):
        ow[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    return ow


def public_readonly_overwrites(guild: discord.Guild) -> dict:
    ow = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True, send_messages=False, add_reactions=True, read_message_history=True
        )
    }
    for role in staff_roles(guild):
        ow[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, add_reactions=True, read_message_history=True)
    return ow


def member_text_overwrites(guild: discord.Guild) -> dict:
    member = find_role(guild, ROLE_MEMBER)
    ow = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
    if member:
        ow[member] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, add_reactions=True,
            read_message_history=True, attach_files=True, embed_links=True,
            use_external_emojis=True, use_external_stickers=True,
            create_public_threads=True, send_messages_in_threads=True,
        )
    for role in staff_roles(guild):
        ow[role] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, add_reactions=True,
            read_message_history=True, attach_files=True, embed_links=True,
        )
    return ow


def member_readonly_overwrites(guild: discord.Guild, reactions: bool = True) -> dict:
    member = find_role(guild, ROLE_MEMBER)
    ow = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
    if member:
        ow[member] = discord.PermissionOverwrite(
            view_channel=True, send_messages=False, add_reactions=reactions, read_message_history=True
        )
    for role in staff_roles(guild):
        ow[role] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, add_reactions=True, read_message_history=True
        )
    return ow


def member_voice_overwrites(guild: discord.Guild) -> dict:
    member = find_role(guild, ROLE_MEMBER)
    ow = {guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False)}
    if member:
        ow[member] = discord.PermissionOverwrite(
            view_channel=True, connect=True, speak=True, stream=True, use_voice_activation=True
        )
    for role in staff_roles(guild):
        ow[role] = discord.PermissionOverwrite(
            view_channel=True, connect=True, speak=True, stream=True,
            use_voice_activation=True, move_members=True, mute_members=True, deafen_members=True
        )
    return ow


def staff_overwrites(guild: discord.Guild) -> dict:
    ow = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
    for role in staff_roles(guild):
        ow[role] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, add_reactions=True,
            read_message_history=True, attach_files=True, embed_links=True
        )
    return ow


async def ensure_category(guild: discord.Guild, name: str, overwrites: dict) -> discord.CategoryChannel:
    category = find_category(guild, name)
    if category is None:
        return await guild.create_category(name, overwrites=overwrites, reason="Setup Zabi Army")
    if category.overwrites != overwrites:
        await category.edit(overwrites=overwrites, reason="Actualizar permisos Zabi Army")
    return category


async def ensure_text(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    name: str,
    overwrites: dict,
    topic: str,
) -> discord.TextChannel:
    channel = find_text(guild, name)
    if channel is None:
        return await guild.create_text_channel(
            name, category=category, overwrites=overwrites, topic=topic, reason="Setup Zabi Army"
        )

    # IMPORTANTE: no cambia el nombre de un canal existente.
    edits = {}
    if channel.category_id != category.id:
        edits["category"] = category
    if channel.overwrites != overwrites:
        edits["overwrites"] = overwrites
    if channel.topic != topic:
        edits["topic"] = topic
    if edits:
        await channel.edit(**edits, reason="Sincronizar Zabi Army sin renombrar")
    return channel


async def ensure_voice(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    name: str,
    overwrites: dict,
) -> discord.VoiceChannel:
    channel = find_voice(guild, name)
    if channel is None:
        return await guild.create_voice_channel(
            name, category=category, overwrites=overwrites, reason="Setup Zabi Army"
        )
    edits = {}
    if channel.category_id != category.id:
        edits["category"] = category
    if channel.overwrites != overwrites:
        edits["overwrites"] = overwrites
    if edits:
        await channel.edit(**edits, reason="Sincronizar Zabi Army sin renombrar")
    return channel


async def bot_embed_messages(channel: discord.TextChannel, title: str, limit: int = 300) -> list[discord.Message]:
    me = channel.guild.me
    if me is None:
        return []
    found = []
    try:
        async for message in channel.history(limit=limit):
            if message.author.id == me.id and message.embeds and message.embeds[0].title == title:
                found.append(message)
    except (discord.Forbidden, discord.HTTPException):
        pass
    return found


async def ensure_embed_message(
    channel: discord.TextChannel,
    title: str,
    description: str,
    colour: discord.Colour = discord.Colour.purple(),
    view: Optional[discord.ui.View] = None,
) -> discord.Message:
    matches = await bot_embed_messages(channel, title)
    embed = discord.Embed(title=title, description=description, colour=colour)
    if matches:
        keep = matches[0]
        try:
            await keep.edit(embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none())
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass
        for duplicate in matches[1:]:
            try:
                await duplicate.delete()
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                pass
        return keep
    return await channel.send(embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none())


async def ensure_guide(
    channel: discord.TextChannel,
    title: str,
    description: str,
    colour: discord.Colour = discord.Colour.blurple(),
) -> discord.Message:
    return await ensure_embed_message(
        channel, f"{GUIDE_PREFIX}{title}", description, colour=colour
    )


# ──────────────────────────────────────────────────────────────────────────────
# VERIFICACIÓN / BIENVENIDAS
# ──────────────────────────────────────────────────────────────────────────────

async def send_welcome(member: discord.Member) -> None:
    channel = find_text(member.guild, CH_WELCOME)
    if channel is None:
        return
    general = find_text(member.guild, CH_GENERAL)
    count = member.guild.member_count or len(member.guild.members)
    embed = discord.Embed(
        title="👹 Un nuevo miembro llegó a Zabi Army",
        description=(
            f"¡Bienvenido/a {member.mention}! Ya sos parte de **Zabi Army**.\n\n"
            + (f"💬 Pasate por {general.mention} y saludá.\n" if general else "")
            + f"✨ Ahora somos **{count} miembros**."
        ),
        colour=discord.Colour.purple(),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    try:
        await channel.send(
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=[member], roles=False, everyone=False),
        )
    except (discord.Forbidden, discord.HTTPException):
        pass


class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Entrar a Zabi Army",
        emoji="👹",
        style=discord.ButtonStyle.success,
        custom_id="zabi:verify",
    )
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return
        role = find_role(interaction.guild, ROLE_MEMBER)
        if role is None:
            return await interaction.response.send_message(
                "No encuentro el rol de Miembro. Un administrador debe ejecutar `/setup`.", ephemeral=True
            )
        if role in interaction.user.roles:
            return await interaction.response.send_message("Ya estás verificado/a ✅", ephemeral=True)
        try:
            await interaction.user.add_roles(role, reason="Verificación automática Zabi Army")
        except discord.Forbidden:
            return await interaction.response.send_message(
                "No pude darte el rol. El rol del bot debe estar por encima de `✅・Miembro`.", ephemeral=True
            )
        await interaction.response.send_message("✅ Listo. Ya tenés acceso al servidor.", ephemeral=True)
        await send_welcome(interaction.user)


# ──────────────────────────────────────────────────────────────────────────────
# ROLES DE PERFIL
# ──────────────────────────────────────────────────────────────────────────────

async def set_exclusive_role(
    interaction: discord.Interaction,
    selected_name: str,
    group: list[str],
    reason: str,
) -> None:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        return
    selected = find_role(interaction.guild, selected_name)
    if selected is None:
        return await interaction.response.send_message("Ese rol todavía no existe.", ephemeral=True)
    roles = [find_role(interaction.guild, name) for name in group]
    roles = [r for r in roles if r is not None]
    to_remove = [r for r in roles if r in interaction.user.roles and r != selected]
    try:
        if to_remove:
            await interaction.user.remove_roles(*to_remove, reason=reason)
        if selected not in interaction.user.roles:
            await interaction.user.add_roles(selected, reason=reason)
        await interaction.response.send_message(f"✅ Tu rol ahora es **{selected.name}**.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("No puedo administrar esos roles. Revisá mi jerarquía.", ephemeral=True)


class CountrySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=name.split("・", 1)[1], value=name, emoji=name.split("・", 1)[0])
            for name in COUNTRIES
        ]
        super().__init__(
            placeholder="🌎 Elegí tu país",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="zabi:roles:country",
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        await set_exclusive_role(interaction, self.values[0], COUNTRIES, "País visual")


class AgeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=name.split("・", 1)[1], value=name, emoji=name.split("・", 1)[0])
            for name in AGE_ROLES
        ]
        super().__init__(
            placeholder="🎂 Elegí tu rango de edad",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="zabi:roles:age",
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        await set_exclusive_role(interaction, self.values[0], AGE_ROLES, "Rango de edad visual")


class RankSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=name.split("・", 1)[1], value=name, emoji=name.split("・", 1)[0])
            for name in VALORANT_RANKS
        ]
        super().__init__(
            placeholder="🔫 Elegí tu rango de Valorant",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="zabi:roles:rank",
            row=2,
        )

    async def callback(self, interaction: discord.Interaction):
        await set_exclusive_role(interaction, self.values[0], VALORANT_RANKS, "Rango de Valorant visual")


class ToggleRoleButton(discord.ui.Button):
    def __init__(self, label: str, emoji: str, role_name: str, row: int):
        self.role_name = role_name
        super().__init__(
            label=label,
            emoji=emoji,
            style=discord.ButtonStyle.secondary,
            custom_id=f"zabi:roles:toggle:{normalized_name(role_name)}",
            row=row,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return
        member_role = find_role(interaction.guild, ROLE_MEMBER)
        if member_role and member_role not in interaction.user.roles and not is_staff(interaction.user):
            return await interaction.response.send_message("Primero verificáte.", ephemeral=True)
        role = find_role(interaction.guild, self.role_name)
        if role is None:
            return await interaction.response.send_message("Ese rol todavía no existe.", ephemeral=True)
        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role, reason="Self role Zabi Army")
                return await interaction.response.send_message(f"➖ Te quité **{role.name}**.", ephemeral=True)
            await interaction.user.add_roles(role, reason="Self role Zabi Army")
            await interaction.response.send_message(f"➕ Ahora tenés **{role.name}**.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("No puedo administrar ese rol. Revisá mi jerarquía.", ephemeral=True)


class RolePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CountrySelect())
        self.add_item(AgeSelect())
        self.add_item(RankSelect())
        self.add_item(ToggleRoleButton("Directos", "🔔", ROLE_LIVE_NOTIFY, 3))
        self.add_item(ToggleRoleButton("Eventos", "🎉", ROLE_EVENT_NOTIFY, 3))
        self.add_item(ToggleRoleButton("Valorant", "🔫", ROLE_GAME_VALORANT, 3))
        self.add_item(ToggleRoleButton("Minecraft", "⛏️", ROLE_GAME_MINECRAFT, 3))
        self.add_item(ToggleRoleButton("Otros juegos", "🎮", ROLE_GAME_OTHER, 4))
        self.add_item(ToggleRoleButton("PC", "🖥️", ROLE_PLATFORM_PC, 4))
        self.add_item(ToggleRoleButton("Consola", "🎮", ROLE_PLATFORM_CONSOLE, 4))
        self.add_item(ToggleRoleButton("Mobile", "📱", ROLE_PLATFORM_MOBILE, 4))


def get_member_valorant_rank(member: discord.Member) -> str:
    names = {role.name for role in member.roles}
    for role_name in reversed(VALORANT_RANKS):
        if role_name in names:
            return role_name
    return "⚫・Sin rango"


# ──────────────────────────────────────────────────────────────────────────────
# SUGERENCIAS
# ──────────────────────────────────────────────────────────────────────────────

def set_embed_field(embed: discord.Embed, name: str, value: str, inline: bool = False) -> None:
    for index, field in enumerate(embed.fields):
        if field.name == name:
            embed.set_field_at(index, name=name, value=value, inline=inline)
            return
    embed.add_field(name=name, value=value, inline=inline)


def suggestion_is_message(message: discord.Message) -> bool:
    if not message.embeds or not message.embeds[0].footer:
        return False
    return (message.embeds[0].footer.text or "").startswith(SUGGESTION_FOOTER_PREFIX)


async def count_reaction_users(message: discord.Message, emoji: str) -> int:
    for reaction in message.reactions:
        if str(reaction.emoji) != emoji:
            continue
        total = 0
        try:
            async for user in reaction.users(limit=None):
                if not user.bot:
                    total += 1
        except (discord.Forbidden, discord.HTTPException):
            return max(0, reaction.count - 1)
        return total
    return 0


async def update_suggestion_votes(message: discord.Message) -> None:
    if not suggestion_is_message(message):
        return
    up = await count_reaction_users(message, "👍")
    down = await count_reaction_users(message, "👎")
    embed = discord.Embed.from_dict(message.embeds[0].to_dict())
    set_embed_field(embed, "🗳️ Votación", f"👍 **{up}** a favor   •   👎 **{down}** en contra", False)
    try:
        await message.edit(embed=embed, view=SuggestionStaffView())
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        pass


class SuggestionModal(discord.ui.Modal, title="Enviar sugerencia"):
    suggestion_title = discord.ui.TextInput(label="Título", placeholder="Ej: Noche de Valorant", max_length=100)
    suggestion_description = discord.ui.TextInput(
        label="Descripción",
        placeholder="Contanos tu idea de forma clara...",
        style=discord.TextStyle.paragraph,
        max_length=1500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        channel = find_text(interaction.guild, CH_SUGGESTIONS)
        if channel is None:
            return await interaction.response.send_message("No encuentro el canal de sugerencias.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        embed = discord.Embed(
            title=f"💡 {safe_text(self.suggestion_title.value, 100)}",
            description=safe_text(self.suggestion_description.value, 1500),
            colour=discord.Colour.gold(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="👤 Propuesta por", value=interaction.user.mention, inline=True)
        embed.add_field(name="📌 Estado", value="🟡 Pendiente", inline=True)
        embed.add_field(name="🗳️ Votación", value="👍 **0** a favor   •   👎 **0** en contra", inline=False)
        embed.set_footer(text=f"{SUGGESTION_FOOTER_PREFIX}author={interaction.user.id}|status=pending")
        message = await channel.send(embed=embed, view=SuggestionStaffView(), allowed_mentions=discord.AllowedMentions.none())
        for emoji in ("👍", "👎"):
            try:
                await message.add_reaction(emoji)
            except (discord.Forbidden, discord.HTTPException):
                pass
        await interaction.followup.send(f"✅ Tu sugerencia fue publicada: {message.jump_url}", ephemeral=True)


class SuggestionPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Enviar sugerencia", emoji="💡", style=discord.ButtonStyle.primary, custom_id="zabi:suggestion:new")
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SuggestionModal())


class SuggestionStaffView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def change_status(self, interaction: discord.Interaction, status: str, label: str, colour: discord.Colour):
        if interaction.guild is None or not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
            return await interaction.response.send_message("Solo el staff puede cambiar el estado.", ephemeral=True)
        if interaction.message is None or not interaction.message.embeds:
            return
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed.from_dict(interaction.message.embeds[0].to_dict())
        set_embed_field(embed, "📌 Estado", label, True)
        footer = embed.footer.text or ""
        footer = re.sub(r"status=[^|]+", f"status={status}", footer)
        embed.set_footer(text=footer)
        embed.colour = colour
        await interaction.message.edit(embed=embed, view=self)
        await interaction.followup.send(f"✅ Estado cambiado a **{label}**.", ephemeral=True)

    @discord.ui.button(label="En revisión", emoji="🟡", style=discord.ButtonStyle.secondary, custom_id="zabi:suggestion:review")
    async def review(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.change_status(interaction, "review", "🟡 En revisión", discord.Colour.orange())

    @discord.ui.button(label="Aceptar", emoji="✅", style=discord.ButtonStyle.success, custom_id="zabi:suggestion:accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.change_status(interaction, "accepted", "✅ Aceptada", discord.Colour.green())

    @discord.ui.button(label="Rechazar", emoji="❌", style=discord.ButtonStyle.danger, custom_id="zabi:suggestion:reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.change_status(interaction, "rejected", "❌ Rechazada", discord.Colour.red())


async def handle_suggestion_reaction(payload: discord.RawReactionActionEvent, added: bool) -> None:
    if payload.guild_id is None or str(payload.emoji) not in {"👍", "👎"}:
        return
    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return
    channel = guild.get_channel(payload.channel_id)
    suggestions = find_text(guild, CH_SUGGESTIONS)
    if not isinstance(channel, discord.TextChannel) or suggestions is None or channel.id != suggestions.id:
        return
    try:
        message = await channel.fetch_message(payload.message_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return
    if not suggestion_is_message(message):
        return

    if added:
        member = guild.get_member(payload.user_id)
        if member is not None and not member.bot:
            opposite = "👎" if str(payload.emoji) == "👍" else "👍"
            for reaction in message.reactions:
                if str(reaction.emoji) == opposite:
                    try:
                        await reaction.remove(member)
                    except (discord.Forbidden, discord.HTTPException):
                        pass
                    break
    try:
        message = await channel.fetch_message(payload.message_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return
    await update_suggestion_votes(message)


# ──────────────────────────────────────────────────────────────────────────────
# TICKETS
# ──────────────────────────────────────────────────────────────────────────────

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

        await interaction.response.send_message("🔒 Cerrando ticket...", ephemeral=True)
        reports = find_text(interaction.guild, CH_REPORTS)
        if reports:
            try:
                await reports.send(
                    f"🔒 {interaction.user.mention} cerró `{interaction.channel.name}`.",
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.Forbidden:
                pass
        await asyncio.sleep(2)
        try:
            await interaction.channel.delete(reason=f"Ticket cerrado por {interaction.user}")
        except (discord.NotFound, discord.Forbidden):
            pass


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir ticket", emoji="🎫", style=discord.ButtonStyle.success, custom_id="zabi:ticket:open")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return
        guild = interaction.guild
        member_role = find_role(guild, ROLE_MEMBER)
        if member_role and member_role not in interaction.user.roles and not is_staff(interaction.user):
            return await interaction.response.send_message("Primero verificáte para abrir un ticket.", ephemeral=True)

        category = find_category(guild, CAT_TICKETS)
        if category is None:
            return await interaction.response.send_message("No encuentro la categoría de tickets.", ephemeral=True)

        for channel in category.text_channels:
            if ticket_owner_id(channel) == interaction.user.id:
                return await interaction.response.send_message(f"Ya tenés un ticket abierto: {channel.mention}", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
                attach_files=True, embed_links=True,
            ),
        }
        if guild.me:
            overwrites[guild.me] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_messages=True, read_message_history=True
            )
        for role in staff_roles(guild):
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True, manage_messages=True
            )

        safe_name = re.sub(r"[^a-z0-9-]", "", interaction.user.name.lower().replace(" ", "-"))[:35] or str(interaction.user.id)
        try:
            channel = await guild.create_text_channel(
                f"🔒・ticket-{safe_name}",
                category=category,
                overwrites=overwrites,
                topic=f"ticket_owner:{interaction.user.id}|status:open",
                reason=f"Ticket abierto por {interaction.user}",
            )
        except discord.Forbidden:
            return await interaction.response.send_message("No pude crear el ticket. Me falta Gestionar canales.", ephemeral=True)

        embed = discord.Embed(
            title="🎫 Ticket privado",
            description=(
                f"Hola {interaction.user.mention}. Contanos qué necesitás y el staff te responde por acá.\n\n"
                "Cuando terminen, usen **Cerrar ticket**."
            ),
            colour=discord.Colour.purple(),
        )
        await channel.send(content=interaction.user.mention, embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Ticket creado: {channel.mention}", ephemeral=True)

        reports = find_text(guild, CH_REPORTS)
        if reports:
            await reports.send(
                f"🎫 {interaction.user.mention} abrió {channel.mention}.",
                allowed_mentions=discord.AllowedMentions.none(),
            )


# ──────────────────────────────────────────────────────────────────────────────
# PARTY / BUSCAR GRUPO
# ──────────────────────────────────────────────────────────────────────────────

def parse_party_footer(embed: discord.Embed):
    footer = embed.footer.text or ""
    match = re.search(r"party_owner:(\d+)\|max:(\d+)\|closed:(0|1)", footer)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), match.group(3) == "1"


def parse_party_members(embed: discord.Embed) -> list[int]:
    for field in embed.fields:
        if field.name == "👥 Jugadores":
            return [int(value) for value in re.findall(r"<@!?(\d+)>", field.value)]
    return []


def set_party_members(embed: discord.Embed, member_ids: list[int], max_players: int):
    value = "\n".join(f"<@{member_id}>" for member_id in member_ids) or "—"
    value += f"\n\n**{len(member_ids)}/{max_players}**"
    for index, field in enumerate(embed.fields):
        if field.name == "👥 Jugadores":
            embed.set_field_at(index, name="👥 Jugadores", value=value, inline=False)
            return


class PartyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Unirme", emoji="✅", style=discord.ButtonStyle.success, custom_id="zabi:party:join")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.message is None or not interaction.message.embeds or not isinstance(interaction.user, discord.Member):
            return
        embed = interaction.message.embeds[0].copy()
        state = parse_party_footer(embed)
        if state is None:
            return await interaction.response.send_message("No pude leer esta búsqueda.", ephemeral=True)
        owner_id, max_players, closed = state
        members = parse_party_members(embed)
        if closed:
            return await interaction.response.send_message("Esta búsqueda está cerrada.", ephemeral=True)
        if interaction.user.id in members:
            return await interaction.response.send_message("Ya estás en el grupo.", ephemeral=True)
        if len(members) >= max_players:
            return await interaction.response.send_message("El grupo ya está completo.", ephemeral=True)
        members.append(interaction.user.id)
        set_party_members(embed, members, max_players)
        if len(members) >= max_players:
            embed.title = "✅ Grupo completo — Valorant"
            embed.colour = discord.Colour.green()
        await interaction.response.edit_message(embed=embed, view=PartyView())

    @discord.ui.button(label="Salir", emoji="🚪", style=discord.ButtonStyle.secondary, custom_id="zabi:party:leave")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.message is None or not interaction.message.embeds or not isinstance(interaction.user, discord.Member):
            return
        embed = interaction.message.embeds[0].copy()
        state = parse_party_footer(embed)
        if state is None:
            return await interaction.response.send_message("No pude leer esta búsqueda.", ephemeral=True)
        owner_id, max_players, closed = state
        members = parse_party_members(embed)
        if interaction.user.id == owner_id:
            return await interaction.response.send_message("Si sos quien creó el grupo, usá **Cerrar**.", ephemeral=True)
        if interaction.user.id not in members:
            return await interaction.response.send_message("No estabas en el grupo.", ephemeral=True)
        members.remove(interaction.user.id)
        set_party_members(embed, members, max_players)
        embed.title = "👥 Buscando gente — Valorant"
        embed.colour = discord.Colour.blurple()
        await interaction.response.edit_message(embed=embed, view=PartyView())

    @discord.ui.button(label="Cerrar", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="zabi:party:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.message is None or not interaction.message.embeds or not isinstance(interaction.user, discord.Member):
            return
        embed = interaction.message.embeds[0].copy()
        state = parse_party_footer(embed)
        if state is None:
            return
        owner_id, max_players, closed = state
        if interaction.user.id != owner_id and not is_staff(interaction.user):
            return await interaction.response.send_message("Solo quien creó la búsqueda o el staff puede cerrarla.", ephemeral=True)
        embed.title = "🔒 Búsqueda cerrada — Valorant"
        embed.colour = discord.Colour.dark_grey()
        embed.set_footer(text=f"party_owner:{owner_id}|max:{max_players}|closed:1")
        await interaction.response.edit_message(embed=embed, view=None)


# ──────────────────────────────────────────────────────────────────────────────
# TWITCH: DIRECTOS + CLIPS
# ──────────────────────────────────────────────────────────────────────────────

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


async def fetch_twitch_stream() -> Optional[dict]:
    data = await twitch_get("streams", {"user_login": TWITCH_CHANNEL})
    streams = data.get("data") or []
    return streams[0] if streams else None


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


def twitch_url() -> str:
    return f"https://www.twitch.tv/{TWITCH_CHANNEL}"


def twitch_embed(stream: dict, test: bool = False) -> discord.Embed:
    display_name = stream.get("user_name") or TWITCH_CHANNEL
    title = stream.get("title") or "Estamos en directo"
    game = stream.get("game_name") or "Sin categoría"
    viewers = stream.get("viewer_count", 0)
    embed = discord.Embed(
        title=f"{'🧪 PRUEBA • ' if test else ''}🔴 {display_name} está EN DIRECTO",
        url=twitch_url(),
        description=f"**{safe_text(title, 500)}**",
        colour=discord.Colour.red(),
    )
    embed.add_field(name="🎮 Categoría", value=safe_text(game, 100), inline=True)
    embed.add_field(name="👀 Espectadores", value=str(viewers), inline=True)
    started = stream.get("started_at")
    if started:
        embed.add_field(name="🕒 Empezó", value=started.replace("T", " ").replace("Z", " UTC"), inline=False)
    thumb = stream.get("thumbnail_url")
    if thumb:
        embed.set_image(url=thumb.replace("{width}", "1280").replace("{height}", "720"))
    embed.set_footer(text=f"Twitch stream ID: {stream.get('id') or 'TEST'}")
    return embed


def twitch_link_view() -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Ver en Twitch", emoji="🟣", style=discord.ButtonStyle.link, url=twitch_url()))
    return view


def twitch_streamer_members(guild: discord.Guild) -> list[discord.Member]:
    if STREAMER_DISCORD_ID:
        member = guild.get_member(STREAMER_DISCORD_ID)
        if member:
            return [member]
    role = find_role(guild, ROLE_STREAMER)
    return list(role.members) if role else []


async def add_live_role(guild: discord.Guild) -> int:
    role = find_role(guild, ROLE_LIVE)
    if role is None:
        role = await ensure_role(guild, ROLE_LIVE, discord.Permissions.none(), 0xED4245, True)
    count = 0
    for member in twitch_streamer_members(guild):
        if role not in member.roles:
            try:
                await member.add_roles(role, reason="Streamer en directo")
                count += 1
            except discord.Forbidden:
                pass
    return count


async def remove_live_role(guild: discord.Guild) -> None:
    role = find_role(guild, ROLE_LIVE)
    if role is None:
        return
    for member in twitch_streamer_members(guild):
        if role in member.roles:
            try:
                await member.remove_roles(role, reason="Terminó el directo")
            except discord.Forbidden:
                pass


def live_text_overwrites(guild: discord.Guild) -> dict:
    return member_text_overwrites(guild)


def live_voice_overwrites(guild: discord.Guild) -> dict:
    return member_voice_overwrites(guild)


async def ensure_live_text(guild: discord.Guild, stream: dict) -> discord.TextChannel:
    category = find_category(guild, CAT_COMMUNITY)
    if category is None:
        raise RuntimeError("No encuentro la categoría ZABI ARMY")
    channel = discord.utils.get(guild.text_channels, name=CH_LIVE)
    topic = f"🔴 EN DIRECTO • {stream.get('game_name') or 'Sin categoría'} • {stream.get('title') or ''}"[:1024]
    if channel is None:
        channel = await guild.create_text_channel(
            CH_LIVE, category=category, overwrites=live_text_overwrites(guild), topic=topic,
            reason="Zabi empezó directo",
        )
    else:
        edits = {}
        if channel.category_id != category.id:
            edits["category"] = category
        if channel.topic != topic:
            edits["topic"] = topic
        if edits:
            await channel.edit(**edits, reason="Actualizar canal de directo")
    return channel


async def ensure_live_voice(guild: discord.Guild) -> discord.VoiceChannel:
    category = find_category(guild, CAT_VOICE)
    if category is None:
        raise RuntimeError("No encuentro la categoría de voz")
    channel = discord.utils.get(guild.voice_channels, name=VC_LIVE)
    if channel is None:
        channel = await guild.create_voice_channel(
            VC_LIVE, category=category, overwrites=live_voice_overwrites(guild), reason="Zabi empezó directo"
        )
    return channel


async def stream_already_announced(channel: discord.TextChannel, stream_id: str) -> bool:
    wanted = f"Twitch stream ID: {stream_id}"
    try:
        async for message in channel.history(limit=100):
            if message.author == channel.guild.me and message.embeds:
                if message.embeds[0].footer and message.embeds[0].footer.text == wanted:
                    return True
    except discord.Forbidden:
        pass
    return False


async def announce_stream(guild: discord.Guild, stream: dict, test: bool = False) -> None:
    channel = find_text(guild, CH_ANNOUNCEMENTS)
    if channel is None:
        return
    stream_id = str(stream.get("id") or "TEST")
    if not test and await stream_already_announced(channel, stream_id):
        return
    notify_role = find_role(guild, ROLE_LIVE_NOTIFY)
    content = None if test or notify_role is None else notify_role.mention
    changed = False
    if notify_role and not notify_role.mentionable and guild.me and notify_role < guild.me.top_role:
        try:
            await notify_role.edit(mentionable=True, reason="Aviso Twitch")
            changed = True
        except discord.Forbidden:
            pass
    try:
        await channel.send(
            content=content,
            embed=twitch_embed(stream, test=test),
            view=twitch_link_view(),
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=False, roles=[notify_role] if content and notify_role else False
            ),
        )
    finally:
        if changed:
            try:
                await notify_role.edit(mentionable=False, reason="Fin aviso Twitch")
            except discord.Forbidden:
                pass


async def handle_twitch_online(guild: discord.Guild, stream: dict, test: bool = False) -> None:
    global _twitch_was_live, _twitch_last_stream_id, _twitch_delete_task
    stream_id = str(stream.get("id") or "TEST")
    first = _twitch_was_live is not True or _twitch_last_stream_id != stream_id

    if _twitch_delete_task and not _twitch_delete_task.done():
        _twitch_delete_task.cancel()
        _twitch_delete_task = None

    live_text = await ensure_live_text(guild, stream)
    live_voice = await ensure_live_voice(guild)
    await add_live_role(guild)

    if first:
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Streaming(name=f"{stream.get('user_name') or TWITCH_CHANNEL} en Twitch", url=twitch_url()),
        )
        await announce_stream(guild, stream, test=test)
        try:
            await live_text.send(
                "🔊 **Canal de voz del directo:** " + live_voice.mention + "\n"
                "⚠️ Al entrar, tu voz puede escucharse en Twitch. Entrá con respeto.",
                embed=twitch_embed(stream, test=test),
                view=twitch_link_view(),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.Forbidden:
            pass

    _twitch_was_live = True
    _twitch_last_stream_id = stream_id


async def delete_live_later(guild_id: int) -> None:
    global _twitch_delete_task
    try:
        if TWITCH_OFFLINE_DELETE_DELAY:
            await asyncio.sleep(TWITCH_OFFLINE_DELETE_DELAY)
        guild = bot.get_guild(guild_id)
        if guild is None:
            return
        if TWITCH_ENABLED and not _twitch_test_mode:
            try:
                if await fetch_twitch_stream() is not None:
                    return
            except Exception:
                return
        for channel in (
            discord.utils.get(guild.text_channels, name=CH_LIVE),
            discord.utils.get(guild.voice_channels, name=VC_LIVE),
        ):
            if channel:
                try:
                    await channel.delete(reason="Terminó el directo")
                except (discord.Forbidden, discord.NotFound):
                    pass
    finally:
        _twitch_delete_task = None


async def handle_twitch_offline(guild: discord.Guild) -> None:
    global _twitch_was_live, _twitch_last_stream_id, _twitch_delete_task
    was_live = _twitch_was_live is True
    await remove_live_role(guild)
    await bot.change_presence(activity=discord.Game(name="Zabi Army 👹"))

    live_text = discord.utils.get(guild.text_channels, name=CH_LIVE)
    live_voice = discord.utils.get(guild.voice_channels, name=VC_LIVE)
    if (live_text or live_voice) and (_twitch_delete_task is None or _twitch_delete_task.done()):
        if was_live and live_text:
            try:
                await live_text.send("🌙 **El directo terminó.** Gracias por acompañar 💜")
            except discord.Forbidden:
                pass
        _twitch_delete_task = asyncio.create_task(delete_live_later(guild.id))

    _twitch_was_live = False
    _twitch_last_stream_id = None


def twitch_test_stream() -> dict:
    return {
        "id": "TEST-STREAM",
        "user_name": TWITCH_CHANNEL or "Zabi",
        "title": "Vista previa del directo de Zabi Army",
        "game_name": "VALORANT",
        "viewer_count": 123,
        "started_at": discord.utils.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "thumbnail_url": "",
    }


@tasks.loop(seconds=TWITCH_POLL_SECONDS)
async def twitch_watch():
    if _twitch_test_mode or not TWITCH_ENABLED or not GUILD_ID:
        return
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        return
    try:
        stream = await fetch_twitch_stream()
        if stream:
            await handle_twitch_online(guild, stream)
        else:
            await handle_twitch_offline(guild)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        print(f"⚠️ Twitch watcher: {type(exc).__name__}: {exc}")


@twitch_watch.before_loop
async def before_twitch_watch():
    await bot.wait_until_ready()


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
    ids = set()
    try:
        async for message in channel.history(limit=500):
            if message.author != channel.guild.me:
                continue
            for embed in message.embeds:
                footer = embed.footer.text if embed.footer else ""
                if footer.startswith("Twitch clip ID: "):
                    ids.add(footer.removeprefix("Twitch clip ID: ").strip())
    except discord.Forbidden:
        pass
    return ids


def clip_embed(clip: dict) -> discord.Embed:
    url = clip.get("url") or twitch_url()
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
    view.add_item(discord.ui.Button(
        label="Ver clip", emoji="🟣", style=discord.ButtonStyle.link, url=clip.get("url") or twitch_url()
    ))
    return view


async def publish_new_clips(guild: discord.Guild) -> tuple[int, int]:
    channel = find_text(guild, CH_CLIPS)
    if channel is None:
        raise RuntimeError("No encuentro el canal de clips")
    clips = await fetch_recent_clips()
    already = await posted_clip_ids(channel)
    pending = [clip for clip in clips if str(clip.get("id")) not in already]
    for clip in pending[-10:]:
        await channel.send(embed=clip_embed(clip), view=clip_view(clip))
    return len(clips), min(len(pending), 10)


@tasks.loop(seconds=TWITCH_CLIPS_POLL_SECONDS)
async def clips_watch():
    if not TWITCH_ENABLED or not GUILD_ID:
        return
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        return
    try:
        found, published = await publish_new_clips(guild)
        if published:
            print(f"🎬 Clips: encontrados {found}, publicados {published}")
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        print(f"⚠️ Clips Twitch: {type(exc).__name__}: {exc}")


@clips_watch.before_loop
async def before_clips_watch():
    await bot.wait_until_ready()


# ──────────────────────────────────────────────────────────────────────────────
# GUÍAS / PANELES
# ──────────────────────────────────────────────────────────────────────────────

async def ensure_panels(guild: discord.Guild) -> None:
    verify = find_text(guild, CH_VERIFY)
    rules = find_text(guild, CH_RULES)
    roles = find_text(guild, CH_ROLES)
    suggestions = find_text(guild, CH_SUGGESTIONS)
    tickets = find_text(guild, CH_TICKET_PANEL)

    if verify:
        await ensure_embed_message(
            verify,
            "👹 Bienvenido/a a Zabi Army",
            "Para entrar al resto del servidor, tocá el botón de abajo.\n\n"
            "Al verificarte aceptás respetar las reglas de la comunidad.",
            discord.Colour.purple(),
            VerifyView(),
        )

    if rules:
        await ensure_embed_message(
            rules,
            "📜 Las reglas del juego",
            "⚠️ **Si se rompe alguna de estas reglas, puede ser motivo de ban.**\n\n"
            "**1. No discrimines.** No se permite ni se tolera ningún tipo de discriminación.\n\n"
            "**2. No me digan cómo jugar.** Solo juego para divertirme.\n\n"
            "**3. Nada de política.** No se habla de temas de política ni cosas relacionadas.\n\n"
            "**4. Respeto ante todo.** No falten el respeto a ningún miembro del canal, ni a mí.\n\n"
            "**5. No pidan beneficios.** No pidan follows, mod, VIP, suscripción o algo relacionado.\n\n"
            "💜 **Pásenla bien y disfruten.**",
            discord.Colour.dark_purple(),
        )

    if roles:
        await ensure_embed_message(
            roles,
            "🎭 Elegí tus roles",
            "Personalizá tu perfil desde este panel.\n\n"
            "🌎 **País** · 🎂 **Edad** · 🔫 **Rango de Valorant**\n"
            "🎮 **Juegos** · 🖥️ **Plataformas** · 📣 **Avisos**\n\n"
            "País, edad y rango son exclusivos: elegir uno nuevo reemplaza el anterior.",
            discord.Colour.blurple(),
            RolePanelView(),
        )

    if suggestions:
        await ensure_embed_message(
            suggestions,
            SUGGESTION_PANEL_TITLE,
            "¿Tenés una idea para mejorar Zabi Army? Tocá **Enviar sugerencia**.\n"
            "La comunidad puede votar con 👍/👎 y el staff puede marcar su estado.",
            discord.Colour.blurple(),
            SuggestionPanelView(),
        )

    if tickets:
        await ensure_embed_message(
            tickets,
            "🎫 Hablá con el staff",
            "¿Necesitás ayuda, querés reportar algo o hablar en privado? "
            "Abrí un ticket y se crea un canal visible solo para vos y el staff.",
            discord.Colour.blurple(),
            TicketPanelView(),
        )


async def ensure_guides(guild: discord.Guild) -> tuple[int, list[str]]:
    guides = [
        (CH_VERIFY, "Verificación", "Usá el botón de verificación para recibir `✅・Miembro` y desbloquear la comunidad."),
        (CH_RULES, "Reglas", "Canal de **solo lectura** con las reglas oficiales. Incumplirlas puede terminar en sanción o ban."),
        (CH_ANNOUNCEMENTS, "Zabi dice", "Anuncios oficiales de Zabi y del staff. También recibe el aviso automático cuando Zabi prende Twitch."),
        (CH_RESOURCES, "Cosas útiles", "Links, redes, horarios, comandos o recursos importantes de Zabi Army."),
        (CH_ROLES, "Roles", "Elegí país, rango de edad, rango de Valorant, juegos, plataformas y avisos del servidor."),
        (CH_GENERAL, "La plaza", "Chat principal de la comunidad para hablar, conocer gente y pasar el rato."),
        (CH_WELCOME, "Nuevos miembros", "Acá aparecen automáticamente las bienvenidas después de que una persona se verifica."),
        (CH_DELINQUENTS, "Los delincuentes", "Un rincón más informal de la comunidad para charlar y compartir dentro de las reglas."),
        (CH_LATE, "Charlas de madrugada", "Para conversaciones nocturnas, insomnio y charla tranquila cuando el resto duerme."),
        (CH_MEDIA, "Pruebas del delito", "Fotos, capturas, fanarts, imágenes y contenido multimedia de la comunidad."),
        (CH_MEMES, "Meme del día", "Memes y humor de la comunidad, siempre sin ataques personales ni contenido prohibido."),
        (CH_MUSIC, "Musiquita", "Compartí canciones, artistas, playlists y lo que estés escuchando."),
        (CH_CLIPS, "Clips de Zabi", "Los clips nuevos del Twitch de Zabi aparecen **automáticamente** acá. Canal ordenado y de solo lectura."),
        (CH_SUGGESTIONS, "Tirá tu idea", "Usá el botón para enviar una sugerencia. La comunidad vota y el staff puede aprobarla o rechazarla."),
        (CH_GAMING, "Viciando", "Gaming general: hablá de cualquier juego y compartí partidas, noticias o experiencias."),
        (CH_VALORANT, "Ranked y lágrimas", "Todo sobre Valorant: rankeds, agentes, mapas, estrategias, clips y partidas."),
        (CH_LFG, "Busco gente", "Usá `/party` para armar un grupo. Otros miembros pueden entrar, salir y completar la party desde botones."),
        (CH_COMPETITIVE, "Competitivo", "Espacio para customs, competitivo, desafíos y organización de partidas más serias."),
        (CH_TICKET_PANEL, "Abrir ticket", "Panel de soporte privado. Cada usuario puede abrir un ticket visible solo para él/ella y el staff."),
        (CH_STAFF, "La oficina", "Chat privado para coordinación del staff."),
        (CH_REPORTS, "Casos abiertos", "Registro interno de tickets abiertos y cerrados."),
        (CH_LOGS, "Historial", "Registro automático de entradas, salidas, cambios de roles y cambios de canales."),
    ]
    updated = 0
    missing = []
    for channel_name, title, description in guides:
        channel = find_text(guild, channel_name)
        if channel is None:
            missing.append(channel_name)
            continue
        await ensure_guide(channel, title, description)
        updated += 1
    return updated, missing


# ──────────────────────────────────────────────────────────────────────────────
# INSTALACIÓN / ACTUALIZACIÓN
# ──────────────────────────────────────────────────────────────────────────────

async def install_channels(guild: discord.Guild) -> None:
    verify_ow = verification_overwrites(guild)
    public_ro = public_readonly_overwrites(guild)
    member_text = member_text_overwrites(guild)
    member_ro = member_readonly_overwrites(guild)
    member_voice = member_voice_overwrites(guild)
    staff_ow = staff_overwrites(guild)

    entry = await ensure_category(guild, CAT_ENTRY, verify_ow)
    community = await ensure_category(guild, CAT_COMMUNITY, member_text)
    gaming = await ensure_category(guild, CAT_GAMING, member_text)
    voice = await ensure_category(guild, CAT_VOICE, member_voice)
    tickets = await ensure_category(guild, CAT_TICKETS, member_ro)
    staff = await ensure_category(guild, CAT_STAFF, staff_ow)

    await ensure_text(guild, entry, CH_VERIFY, verify_ow, "Verificate para desbloquear Zabi Army.")
    await ensure_text(guild, entry, CH_RULES, public_ro, "Reglas oficiales de Zabi Army.")
    await ensure_text(guild, entry, CH_ANNOUNCEMENTS, public_ro, "Anuncios oficiales y avisos de Twitch.")
    await ensure_text(guild, entry, CH_RESOURCES, public_ro, "Links y recursos útiles.")
    await ensure_text(guild, entry, CH_ROLES, member_ro, "Elegí tus roles de perfil y avisos.")

    await ensure_text(guild, community, CH_GENERAL, member_text, "Chat principal de Zabi Army.")
    await ensure_text(guild, community, CH_WELCOME, member_ro, "Bienvenidas automáticas después de verificar.")
    await ensure_text(guild, community, CH_DELINQUENTS, member_text, "El rincón de los delincuentes.")
    await ensure_text(guild, community, CH_LATE, member_text, "Charlas de madrugada.")
    await ensure_text(guild, community, CH_MEDIA, member_text, "Fotos, capturas y contenido multimedia.")
    await ensure_text(guild, community, CH_MEMES, member_text, "Memes de la comunidad.")
    await ensure_text(guild, community, CH_MUSIC, member_text, "Canciones y playlists.")
    await ensure_text(guild, community, CH_CLIPS, member_ro, "Clips nuevos de Twitch publicados automáticamente.")
    await ensure_text(guild, community, CH_SUGGESTIONS, member_ro, "Sugerencias con votos y estados.")

    await ensure_text(guild, gaming, CH_GAMING, member_text, "Gaming general.")
    await ensure_text(guild, gaming, CH_VALORANT, member_text, "Todo sobre Valorant.")
    await ensure_text(guild, gaming, CH_LFG, member_text, "Buscá gente para jugar.")
    await ensure_text(guild, gaming, CH_COMPETITIVE, member_text, "Customs y competitivo.")

    await ensure_voice(guild, voice, VC_CONFESSIONAL, member_voice)
    await ensure_voice(guild, voice, VC_HELLFIRE, member_voice)
    await ensure_voice(guild, voice, VC_BASEMENT, member_voice)
    await ensure_voice(guild, voice, VC_INSOMNIA, member_voice)
    await ensure_voice(guild, voice, VC_CREATE, member_voice)

    await ensure_text(guild, tickets, CH_TICKET_PANEL, member_ro, "Abrí un ticket privado con el staff.")
    await ensure_text(guild, staff, CH_STAFF, staff_ow, "Chat privado del staff.")
    await ensure_text(guild, staff, CH_REPORTS, staff_ow, "Seguimiento interno de tickets.")
    await ensure_text(guild, staff, CH_LOGS, staff_ow, "Logs y registros de moderación.")


async def install_server(guild: discord.Guild) -> None:
    await ensure_roles(guild)
    await ensure_role_order(guild)
    await install_channels(guild)
    await ensure_panels(guild)
    await ensure_guides(guild)


async def require_admin(interaction: discord.Interaction) -> bool:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        return False
    if not interaction.user.guild_permissions.administrator:
        if interaction.response.is_done():
            await interaction.followup.send("Necesitás Administrador para usar este comando.", ephemeral=True)
        else:
            await interaction.response.send_message("Necesitás Administrador para usar este comando.", ephemeral=True)
        return False
    return True


@bot.tree.command(name="setup", description="Instalación completa inicial de Zabi Army.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await install_server(interaction.guild)
        await interaction.followup.send(
            "✅ **Zabi Army instalado/actualizado.**\n"
            "Roles, permisos, verificación, guías, Twitch, clips, sugerencias, tickets y voz temporal quedaron preparados.\n\n"
            "ℹ️ El bot **no renombra canales existentes**.",
            ephemeral=True,
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Discord bloqueó una acción. El bot necesita Gestionar canales, Gestionar roles, Gestionar mensajes "
            "y Mover miembros; su rol debe estar por encima de los roles que administra.",
            ephemeral=True,
        )
    except Exception as exc:
        await interaction.followup.send(f"❌ `{type(exc).__name__}: {str(exc)[:700]}`", ephemeral=True)
        raise


@bot.tree.command(name="actualizar-canales", description="Actualiza categorías, canales y permisos sin renombrar canales existentes.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def actualizar_canales(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await install_channels(interaction.guild)
        await interaction.followup.send("✅ Canales y permisos actualizados. No se renombró ningún canal existente.", ephemeral=True)
    except Exception as exc:
        await interaction.followup.send(f"❌ `{type(exc).__name__}: {str(exc)[:700]}`", ephemeral=True)


@bot.tree.command(name="actualizar-roles", description="Crea/actualiza todos los roles y el panel de roles.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def actualizar_roles(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await ensure_roles(interaction.guild)
        await ensure_role_order(interaction.guild)
        roles_channel = find_text(interaction.guild, CH_ROLES)
        if roles_channel:
            await ensure_panels(interaction.guild)
        await interaction.followup.send(
            "✅ Roles sincronizados con la misma base del Streamer Bot: staff, Streamer, Subscriber, VIP, Miembro, "
            "avisos, país, edad, rango de Valorant, juegos y plataformas.",
            ephemeral=True,
        )
    except Exception as exc:
        await interaction.followup.send(f"❌ `{type(exc).__name__}: {str(exc)[:700]}`", ephemeral=True)


@bot.tree.command(name="actualizar-guias", description="Crea o actualiza la explicación de cada canal.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def actualizar_guias(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        updated, missing = await ensure_guides(interaction.guild)
        text = f"✅ Guías actualizadas: **{updated}** canales."
        if missing:
            text += "\n⚠️ No encontré: " + ", ".join(f"`{name}`" for name in missing)
        await interaction.followup.send(text, ephemeral=True)
    except Exception as exc:
        await interaction.followup.send(f"❌ `{type(exc).__name__}: {str(exc)[:700]}`", ephemeral=True)


@bot.tree.command(name="actualizar-paneles", description="Actualiza verificación, reglas, roles, sugerencias y tickets.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def actualizar_paneles(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    await ensure_panels(interaction.guild)
    await interaction.followup.send("✅ Paneles actualizados.", ephemeral=True)


@bot.tree.command(name="actualizar-tickets", description="Actualiza el panel y permisos del sistema de tickets.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def actualizar_tickets(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    await install_channels(interaction.guild)
    await ensure_panels(interaction.guild)
    await interaction.followup.send("✅ Sistema de tickets actualizado.", ephemeral=True)


@bot.tree.command(name="party", description="Buscá gente para jugar Valorant.")
@app_commands.guild_only()
@app_commands.describe(modo="Modo de juego", cupos="Cantidad total de jugadores (2 a 5)", servidor="Servidor o región")
async def party(interaction: discord.Interaction, modo: str = "Competitivo", cupos: app_commands.Range[int, 2, 5] = 5, servidor: str = "No especificado"):
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        return
    channel = find_text(interaction.guild, CH_LFG)
    if channel is None:
        return await interaction.response.send_message("No encuentro el canal para buscar gente.", ephemeral=True)
    if interaction.channel_id != channel.id:
        return await interaction.response.send_message(f"Usá `/party` dentro de {channel.mention}.", ephemeral=True)
    member_role = find_role(interaction.guild, ROLE_MEMBER)
    if member_role and member_role not in interaction.user.roles and not is_staff(interaction.user):
        return await interaction.response.send_message("Primero verificáte.", ephemeral=True)

    embed = discord.Embed(
        title="👥 Buscando gente — Valorant",
        description=f"**{interaction.user.display_name}** está armando grupo.",
        colour=discord.Colour.blurple(),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="🎯 Modo", value=safe_text(modo, 80), inline=True)
    embed.add_field(name="🏅 Rango", value=get_member_valorant_rank(interaction.user), inline=True)
    embed.add_field(name="🌐 Servidor", value=safe_text(servidor, 80), inline=True)
    embed.add_field(name="👥 Jugadores", value=f"{interaction.user.mention}\n\n**1/{cupos}**", inline=False)
    embed.set_footer(text=f"party_owner:{interaction.user.id}|max:{cupos}|closed:0")
    await interaction.response.send_message(embed=embed, view=PartyView(), allowed_mentions=discord.AllowedMentions.none())


@bot.tree.command(name="clips-revisar", description="Revisa Twitch ahora mismo y publica clips pendientes.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def clips_revisar(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return
    if not TWITCH_ENABLED:
        return await interaction.response.send_message("Twitch no está configurado.", ephemeral=True)
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        found, published = await publish_new_clips(interaction.guild)
        await interaction.followup.send(
            f"✅ Twitch devolvió **{found}** clips recientes. Publiqué **{published}** nuevos.", ephemeral=True
        )
    except Exception as exc:
        await interaction.followup.send(f"❌ `{type(exc).__name__}: {str(exc)[:700]}`", ephemeral=True)


@bot.tree.command(name="clips-estado", description="Muestra el estado del watcher de clips.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def clips_estado(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🎬 **Clips automáticos**\n"
        f"Watcher: {'✅ activo' if clips_watch.is_running() else '⚠️ detenido'}\n"
        f"Canal Twitch: `@{TWITCH_CHANNEL or 'sin configurar'}`\n"
        f"Revisión: cada **{TWITCH_CLIPS_POLL_SECONDS}s**\n"
        f"Ventana: **{TWITCH_CLIPS_LOOKBACK_MINUTES} min**",
        ephemeral=True,
    )


@bot.tree.command(name="actualizar-twitch", description="Comprueba la integración automática con Twitch.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def actualizar_twitch(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return
    if not TWITCH_ENABLED:
        return await interaction.response.send_message(
            "❌ Faltan TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET o TWITCH_CHANNEL.", ephemeral=True
        )
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        stream = await fetch_twitch_stream()
        if not twitch_watch.is_running():
            twitch_watch.start()
        if not clips_watch.is_running():
            clips_watch.start()
        if stream:
            await handle_twitch_online(interaction.guild, stream)
            text = f"✅ Twitch funcionando. `@{TWITCH_CHANNEL}` está **EN DIRECTO**."
        else:
            await handle_twitch_offline(interaction.guild)
            text = f"✅ Twitch funcionando. `@{TWITCH_CHANNEL}` está offline."
        await interaction.followup.send(text, ephemeral=True)
    except Exception as exc:
        await interaction.followup.send(f"❌ `{type(exc).__name__}: {str(exc)[:700]}`", ephemeral=True)


@bot.tree.command(name="twitch-estado", description="Muestra el estado real de Twitch y de los canales temporales.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def twitch_estado(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return
    if not TWITCH_ENABLED:
        return await interaction.response.send_message("Twitch no está configurado.", ephemeral=True)
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        stream = await fetch_twitch_stream()
        live_text = discord.utils.get(interaction.guild.text_channels, name=CH_LIVE)
        live_voice = discord.utils.get(interaction.guild.voice_channels, name=VC_LIVE)
        await interaction.followup.send(
            "🟣 **Twitch**\n"
            f"Canal: `@{TWITCH_CHANNEL}`\n"
            f"Estado: {'🔴 EN DIRECTO' if stream else '⚫ Offline'}\n"
            f"Texto temporal: {'✅' if live_text else '—'}\n"
            f"Voz temporal: {'✅' if live_voice else '—'}\n"
            f"Watcher: {'✅' if twitch_watch.is_running() else '⚠️'}",
            ephemeral=True,
        )
    except Exception as exc:
        await interaction.followup.send(f"❌ `{type(exc).__name__}: {str(exc)[:700]}`", ephemeral=True)


@bot.tree.command(name="twitch-preview", description="Muestra una vista previa privada del aviso de Twitch.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def twitch_preview(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return
    if not TWITCH_CHANNEL:
        return await interaction.response.send_message("Falta TWITCH_CHANNEL.", ephemeral=True)
    await interaction.response.send_message(
        "🧪 Vista previa privada. No crea canales ni menciona a nadie.",
        embed=twitch_embed(twitch_test_stream(), test=True),
        view=twitch_link_view(),
        ephemeral=True,
    )


@bot.tree.command(name="twitch-simular", description="Simula un directo completo sin prender Twitch.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def twitch_simular(interaction: discord.Interaction):
    global _twitch_test_mode
    if not await require_admin(interaction):
        return
    if not TWITCH_CHANNEL:
        return await interaction.response.send_message("Falta TWITCH_CHANNEL.", ephemeral=True)
    await interaction.response.defer(ephemeral=True, thinking=True)
    _twitch_test_mode = True
    try:
        await handle_twitch_online(interaction.guild, twitch_test_stream(), test=True)
        await interaction.followup.send(
            f"✅ Simulación activa. Revisá `{CH_LIVE}` y `{VC_LIVE}`. Usá `/twitch-fin-prueba` al terminar.",
            ephemeral=True,
        )
    except Exception as exc:
        _twitch_test_mode = False
        await interaction.followup.send(f"❌ `{type(exc).__name__}: {str(exc)[:700]}`", ephemeral=True)


@bot.tree.command(name="twitch-fin-prueba", description="Termina la simulación de Twitch.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def twitch_fin_prueba(interaction: discord.Interaction):
    global _twitch_test_mode, _twitch_was_live, _twitch_last_stream_id
    if not await require_admin(interaction):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    _twitch_test_mode = False
    await remove_live_role(interaction.guild)
    for channel in (
        discord.utils.get(interaction.guild.text_channels, name=CH_LIVE),
        discord.utils.get(interaction.guild.voice_channels, name=VC_LIVE),
    ):
        if channel:
            try:
                await channel.delete(reason="Fin de prueba Twitch")
            except discord.Forbidden:
                pass
    _twitch_was_live = False
    _twitch_last_stream_id = None
    await bot.change_presence(activity=discord.Game(name="Zabi Army 👹"))
    await interaction.followup.send("✅ Simulación terminada y canales de prueba eliminados.", ephemeral=True)


@bot.tree.command(name="bot-estado", description="Revisa las funciones principales de Zabi Army Bot.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def bot_estado(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return
    guild = interaction.guild
    checks = {
        "Verificación": bool(find_role(guild, ROLE_MEMBER) and find_text(guild, CH_VERIFY)),
        "Roles": bool(find_text(guild, CH_ROLES) and find_role(guild, ROLE_STREAMER) and find_role(guild, ROLE_COOWNER)),
        "Clips": bool(find_text(guild, CH_CLIPS) and TWITCH_ENABLED),
        "Sugerencias": bool(find_text(guild, CH_SUGGESTIONS)),
        "Tickets": bool(find_text(guild, CH_TICKET_PANEL) and find_category(guild, CAT_TICKETS)),
        "Crear sala": bool(find_voice(guild, VC_CREATE) and intents.voice_states),
        "Guías": bool(find_text(guild, CH_GENERAL)),
        "Twitch": TWITCH_ENABLED,
    }
    lines = [f"{'✅' if ok else '❌'} {name}" for name, ok in checks.items()]
    await interaction.response.send_message("🤖 **Estado Zabi Army Bot**\n" + "\n".join(lines), ephemeral=True)


# ──────────────────────────────────────────────────────────────────────────────
# LOGS / EVENTOS DISCORD
# ──────────────────────────────────────────────────────────────────────────────

async def send_log(guild: discord.Guild, title: str, description: str, colour: discord.Colour = discord.Colour.blurple()):
    channel = find_text(guild, CH_LOGS)
    if channel is None:
        return
    embed = discord.Embed(title=title, description=description, colour=colour, timestamp=discord.utils.utcnow())
    try:
        await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
    except discord.Forbidden:
        pass


@bot.event
async def on_member_join(member: discord.Member):
    await send_log(member.guild, "📥 Miembro entró", f"{member.mention} (`{member.id}`) se unió al servidor.", discord.Colour.green())


@bot.event
async def on_member_remove(member: discord.Member):
    await send_log(member.guild, "📤 Miembro salió", f"**{member}** (`{member.id}`) salió del servidor.", discord.Colour.orange())


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    before_ids = {role.id for role in before.roles}
    after_ids = {role.id for role in after.roles}
    added = [role.name for role in after.roles if role.id not in before_ids and role != after.guild.default_role]
    removed = [role.name for role in before.roles if role.id not in after_ids and role != after.guild.default_role]
    if added or removed:
        parts = [f"**Usuario:** {after.mention}"]
        if added:
            parts.append("**Agregados:** " + ", ".join(added))
        if removed:
            parts.append("**Quitados:** " + ", ".join(removed))
        await send_log(after.guild, "🎭 Cambio de roles", "\n".join(parts))


@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    if channel.name in {CH_LOGS, CH_REPORTS} or (channel.category and channel.category.name == CAT_TICKETS):
        return
    await send_log(channel.guild, "➕ Canal creado", f"Se creó **{discord.utils.escape_mentions(channel.name)}**.")


@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    if channel.name in {CH_LOGS, CH_REPORTS} or (channel.category and channel.category.name == CAT_TICKETS):
        return
    await send_log(channel.guild, "➖ Canal eliminado", f"Se eliminó **{discord.utils.escape_mentions(channel.name)}**.", discord.Colour.red())


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if bot.user and payload.user_id == bot.user.id:
        return
    await handle_suggestion_reaction(payload, True)


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if bot.user and payload.user_id == bot.user.id:
        return
    await handle_suggestion_reaction(payload, False)


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    create_channel = find_voice(member.guild, VC_CREATE)

    # Entrar a crear-sala => crea una sala personal y mueve al usuario.
    if after.channel and create_channel and after.channel.id == create_channel.id:
        category = after.channel.category
        if category is not None:
            overwrites = dict(category.overwrites)
            overwrites[member] = discord.PermissionOverwrite(
                view_channel=True, connect=True, speak=True, stream=True,
                manage_channels=True, move_members=True, mute_members=True, deafen_members=True,
            )
            try:
                temp = await member.guild.create_voice_channel(
                    f"{TEMP_VC_PREFIX}{member.display_name}"[:100],
                    category=category,
                    overwrites=overwrites,
                    reason="Sala temporal creada automáticamente",
                )
                await member.move_to(temp, reason="Mover a su sala temporal")
            except discord.Forbidden:
                print("⚠️ Crear sala: faltan Gestionar canales o Mover miembros.")
            except discord.HTTPException as exc:
                print(f"⚠️ Crear sala: {exc}")

    # Sala temporal vacía => se elimina.
    if before.channel and before.channel.name.startswith(TEMP_VC_PREFIX):
        await asyncio.sleep(1)
        if len(before.channel.members) == 0:
            try:
                await before.channel.delete(reason="Sala temporal vacía")
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass


# ──────────────────────────────────────────────────────────────────────────────
# HEALTH / ARRANQUE
# ──────────────────────────────────────────────────────────────────────────────

async def health(_request: web.Request) -> web.Response:
    return web.json_response({
        "ok": True,
        "bot": "zabi-army-bot",
        "discord_ready": bot.is_ready(),
        "twitch_enabled": TWITCH_ENABLED,
        "twitch_watch": twitch_watch.is_running(),
        "clips_watch": clips_watch.is_running(),
    })


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
        except discord.Forbidden:
            print("ℹ️ El bot todavía no tiene acceso al GUILD_ID configurado.")
        except Exception as exc:
            print(f"⚠️ Error sincronizando comandos: {exc}")

    await bot.change_presence(activity=discord.Game(name="Zabi Army 👹"))

    if TWITCH_ENABLED:
        if not twitch_watch.is_running():
            twitch_watch.start()
        if not clips_watch.is_running():
            clips_watch.start()
        print(f"🟣 Twitch activo: @{TWITCH_CHANNEL} cada {TWITCH_POLL_SECONDS}s")
        print(f"🎬 Clips activos cada {TWITCH_CLIPS_POLL_SECONDS}s")


async def main():
    if not TOKEN:
        raise RuntimeError("Falta DISCORD_TOKEN")

    bot.add_view(VerifyView())
    bot.add_view(RolePanelView())
    bot.add_view(SuggestionPanelView())
    bot.add_view(SuggestionStaffView())
    bot.add_view(TicketPanelView())
    bot.add_view(CloseTicketView())
    bot.add_view(PartyView())

    runner = await start_health_server()
    try:
        await bot.start(TOKEN)
    finally:
        if twitch_watch.is_running():
            twitch_watch.cancel()
        if clips_watch.is_running():
            clips_watch.cancel()
        if _http_session and not _http_session.closed:
            await _http_session.close()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
