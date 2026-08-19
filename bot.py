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

# ──────────────────────────────────────────────────────────────────────────────
# NOMBRES — identidad propia de Zabi Army
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
CH_STAFF = "🛡️・la-oficina"
CH_REPORTS = "🚨・casos-abiertos"
CH_LOGS = "📜・historial"

ROLE_OWNER = "👑・Owner"
ROLE_STREAMER = "🎥・Zabi"
ROLE_ADMIN = "🛡️・Admin"
ROLE_MOD = "🔨・Moderador"
ROLE_VIP = "💎・VIP"
ROLE_MEMBER = "✅・Miembro"
ROLE_NOTIFY = "🔔・Avisos de Zabi"
ROLE_VALORANT = "🔫・Valorant"
ROLE_MINECRAFT = "⛏️・Minecraft"
ROLE_OTHER_GAMES = "🎮・Otros juegos"
ROLE_PC = "🖥️・PC"
ROLE_CONSOLE = "🎮・Consola"
ROLE_MOBILE = "📱・Mobile"

SELF_ROLES = [
    ("🔔", "Avisos de Zabi", ROLE_NOTIFY),
    ("🔫", "Valorant", ROLE_VALORANT),
    ("⛏️", "Minecraft", ROLE_MINECRAFT),
    ("🎮", "Otros juegos", ROLE_OTHER_GAMES),
    ("🖥️", "PC", ROLE_PC),
    ("🎮", "Consola", ROLE_CONSOLE),
    ("📱", "Mobile", ROLE_MOBILE),
]

# Canales existentes del servidor real que se reutilizan en vez de duplicarse.
ALIASES = {
    CH_VERIFY: ["bienvenida-y-reglas", "bienvenida", "verificacion", "verificación"],
    CH_RULES: ["reglas", "rules"],
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


# ──────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ──────────────────────────────────────────────────────────────────────────────

def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9áéíóúüñ]+", "", value.casefold())


def find_role(guild: discord.Guild, name: str) -> Optional[discord.Role]:
    return discord.utils.get(guild.roles, name=name)


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


def staff_roles(guild: discord.Guild) -> list[discord.Role]:
    names = {ROLE_OWNER, ROLE_STREAMER, ROLE_ADMIN, ROLE_MOD}
    return [role for role in guild.roles if role.name in names]


def is_staff(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    names = {ROLE_OWNER, ROLE_STREAMER, ROLE_ADMIN, ROLE_MOD}
    return any(role.name in names for role in member.roles)


async def ensure_role(
    guild: discord.Guild,
    name: str,
    permissions: discord.Permissions,
    colour: int,
    *,
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
            reason="Instalación Zabi Army Bot",
        )

    me = guild.me
    if me is not None and role >= me.top_role:
        return role
    if role.permissions != permissions or role.colour != wanted_colour or role.hoist != hoist or role.mentionable:
        await role.edit(
            permissions=permissions,
            colour=wanted_colour,
            hoist=hoist,
            mentionable=False,
            reason="Actualizar roles de Zabi Army",
        )
    return role


async def ensure_roles(guild: discord.Guild) -> dict[str, discord.Role]:
    owner = await ensure_role(guild, ROLE_OWNER, discord.Permissions(administrator=True), 0x000000, hoist=False)
    streamer = await ensure_role(guild, ROLE_STREAMER, discord.Permissions.none(), 0xA970FF, hoist=True)
    admin = await ensure_role(guild, ROLE_ADMIN, discord.Permissions(administrator=True), 0xE74C3C, hoist=True)

    mod_perms = discord.Permissions.none()
    for permission in (
        "kick_members",
        "ban_members",
        "moderate_members",
        "manage_messages",
        "manage_nicknames",
        "move_members",
        "mute_members",
        "deafen_members",
        "view_audit_log",
    ):
        setattr(mod_perms, permission, True)
    mod = await ensure_role(guild, ROLE_MOD, mod_perms, 0xE67E22, hoist=True)

    vip = await ensure_role(guild, ROLE_VIP, discord.Permissions.none(), 0xF1C40F, hoist=True)
    member = await ensure_role(guild, ROLE_MEMBER, discord.Permissions.none(), 0x5865F2)
    notify = await ensure_role(guild, ROLE_NOTIFY, discord.Permissions.none(), 0x9146FF)
    valorant = await ensure_role(guild, ROLE_VALORANT, discord.Permissions.none(), 0xFF4655)
    minecraft = await ensure_role(guild, ROLE_MINECRAFT, discord.Permissions.none(), 0x55AA55)
    other_games = await ensure_role(guild, ROLE_OTHER_GAMES, discord.Permissions.none(), 0x99AAB5)
    pc = await ensure_role(guild, ROLE_PC, discord.Permissions.none(), 0x7289DA)
    console = await ensure_role(guild, ROLE_CONSOLE, discord.Permissions.none(), 0x99AAB5)
    mobile = await ensure_role(guild, ROLE_MOBILE, discord.Permissions.none(), 0x99AAB5)

    return {
        ROLE_OWNER: owner,
        ROLE_STREAMER: streamer,
        ROLE_ADMIN: admin,
        ROLE_MOD: mod,
        ROLE_VIP: vip,
        ROLE_MEMBER: member,
        ROLE_NOTIFY: notify,
        ROLE_VALORANT: valorant,
        ROLE_MINECRAFT: minecraft,
        ROLE_OTHER_GAMES: other_games,
        ROLE_PC: pc,
        ROLE_CONSOLE: console,
        ROLE_MOBILE: mobile,
    }


async def ensure_role_order(guild: discord.Guild) -> None:
    me = guild.me
    if me is None:
        return
    ordered = [ROLE_OWNER, ROLE_STREAMER, ROLE_ADMIN, ROLE_MOD, ROLE_VIP, ROLE_MEMBER]
    target = me.top_role.position - 1
    try:
        for name in ordered:
            role = find_role(guild, name)
            if role is None or role >= me.top_role or target <= 0:
                continue
            if role.position != target:
                await role.edit(position=target, reason="Jerarquía visual Zabi Army")
            target -= 1
    except (discord.Forbidden, discord.HTTPException):
        pass


def verification_overwrites(guild: discord.Guild) -> dict:
    ow = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=False,
            add_reactions=False,
            read_message_history=True,
        )
    }
    for role in staff_roles(guild):
        ow[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    return ow


def public_readonly_overwrites(guild: discord.Guild) -> dict:
    ow = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=False,
            add_reactions=True,
            read_message_history=True,
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
            view_channel=True,
            send_messages=True,
            add_reactions=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
            use_external_emojis=True,
            use_external_stickers=True,
            create_public_threads=True,
            send_messages_in_threads=True,
        )
    for role in staff_roles(guild):
        ow[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, add_reactions=True, read_message_history=True, attach_files=True, embed_links=True)
    return ow


def member_readonly_overwrites(guild: discord.Guild, *, reactions: bool = True) -> dict:
    member = find_role(guild, ROLE_MEMBER)
    ow = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
    if member:
        ow[member] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=False,
            add_reactions=reactions,
            read_message_history=True,
        )
    for role in staff_roles(guild):
        ow[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, add_reactions=True, read_message_history=True)
    return ow


def member_voice_overwrites(guild: discord.Guild) -> dict:
    member = find_role(guild, ROLE_MEMBER)
    ow = {guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False)}
    if member:
        ow[member] = discord.PermissionOverwrite(
            view_channel=True,
            connect=True,
            speak=True,
            stream=True,
            use_voice_activation=True,
        )
    for role in staff_roles(guild):
        ow[role] = discord.PermissionOverwrite(
            view_channel=True,
            connect=True,
            speak=True,
            stream=True,
            use_voice_activation=True,
            move_members=True,
            mute_members=True,
            deafen_members=True,
        )
    return ow


def staff_overwrites(guild: discord.Guild) -> dict:
    ow = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
    for role in staff_roles(guild):
        ow[role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            add_reactions=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        )
    return ow


async def ensure_category(guild: discord.Guild, name: str, overwrites: dict) -> discord.CategoryChannel:
    category = find_category(guild, name)
    if category is None:
        return await guild.create_category(name, overwrites=overwrites, reason="Instalación Zabi Army Bot")
    if category.overwrites != overwrites:
        await category.edit(overwrites=overwrites, reason="Actualizar categoría Zabi Army")
    return category


async def ensure_text(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    name: str,
    *,
    topic: str,
    overwrites: dict,
) -> discord.TextChannel:
    channel = find_alias_text(guild, name)
    if channel is None:
        return await guild.create_text_channel(
            name,
            category=category,
            topic=topic,
            overwrites=overwrites,
            reason="Instalación Zabi Army Bot",
        )

    edits = {}
    if channel.name != name:
        edits["name"] = name
    if channel.category_id != category.id:
        edits["category"] = category
    if channel.topic != topic:
        edits["topic"] = topic
    if channel.overwrites != overwrites:
        edits["overwrites"] = overwrites
    if edits:
        await channel.edit(**edits, reason="Migración Zabi Army Bot")
    return channel


async def ensure_voice(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    name: str,
    overwrites: dict,
) -> discord.VoiceChannel:
    channel = find_alias_voice(guild, name)
    if channel is None:
        return await guild.create_voice_channel(
            name,
            category=category,
            overwrites=overwrites,
            reason="Instalación Zabi Army Bot",
        )
    edits = {}
    if channel.name != name:
        edits["name"] = name
    if channel.category_id != category.id:
        edits["category"] = category
    if channel.overwrites != overwrites:
        edits["overwrites"] = overwrites
    if edits:
        await channel.edit(**edits, reason="Migración Zabi Army Bot")
    return channel


async def ensure_embed_message(
    channel: discord.TextChannel,
    *,
    title: str,
    description: str,
    colour: discord.Colour = discord.Colour.purple(),
    view: Optional[discord.ui.View] = None,
) -> discord.Message:
    try:
        async for message in channel.history(limit=60):
            if message.author == channel.guild.me and message.embeds and message.embeds[0].title == title:
                embed = discord.Embed(title=title, description=description, colour=colour)
                await message.edit(embed=embed, view=view)
                return message
    except discord.Forbidden:
        pass
    embed = discord.Embed(title=title, description=description, colour=colour)
    return await channel.send(embed=embed, view=view)


# ──────────────────────────────────────────────────────────────────────────────
# VERIFICACIÓN + BIENVENIDA
# ──────────────────────────────────────────────────────────────────────────────

async def send_welcome(member: discord.Member) -> None:
    channel = find_text(member.guild, CH_WELCOME)
    if channel is None:
        return
    embed = discord.Embed(
        title="😈 Un nuevo delincuente apareció",
        description=(
            f"Bienvenido/a {member.mention} a **Zabi Army**.\n"
            f"Ya somos **{member.guild.member_count or len(member.guild.members)}** por acá.\n\n"
            f"Pasate por {find_text(member.guild, CH_GENERAL).mention if find_text(member.guild, CH_GENERAL) else '#la-plaza'} y hacete sentir."
        ),
        colour=discord.Colour.purple(),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions(users=True))


class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Entrar a Zabi Army",
        emoji="😈",
        style=discord.ButtonStyle.success,
        custom_id="zabi:verify",
    )
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return
        role = find_role(interaction.guild, ROLE_MEMBER)
        if role is None:
            return await interaction.response.send_message("No encuentro el rol de miembro. Avisale al staff.", ephemeral=True)
        if role in interaction.user.roles:
            return await interaction.response.send_message("Ya estás adentro de Zabi Army 😈", ephemeral=True)
        try:
            await interaction.user.add_roles(role, reason="Verificación Zabi Army")
        except discord.Forbidden:
            return await interaction.response.send_message("No puedo darte el rol. El rol del bot debe estar por encima de `✅・Miembro`.", ephemeral=True)
        await interaction.response.send_message("✅ **Listo.** Ya podés ver el resto del servidor. Bienvenido/a a Zabi Army 😈", ephemeral=True)
        await send_welcome(interaction.user)


# ──────────────────────────────────────────────────────────────────────────────
# SELF ROLES
# ──────────────────────────────────────────────────────────────────────────────

class ToggleRoleButton(discord.ui.Button):
    def __init__(self, emoji: str, label: str, role_name: str, row: int):
        self.role_name = role_name
        super().__init__(
            label=label,
            emoji=emoji,
            style=discord.ButtonStyle.secondary,
            custom_id=f"zabi:selfrole:{normalized_name(role_name)}",
            row=row,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return
        member_role = find_role(interaction.guild, ROLE_MEMBER)
        if member_role is not None and member_role not in interaction.user.roles:
            return await interaction.response.send_message("Primero verificáte en el canal de entrada.", ephemeral=True)
        role = find_role(interaction.guild, self.role_name)
        if role is None:
            return await interaction.response.send_message("Ese rol todavía no está disponible.", ephemeral=True)
        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role, reason="Self role Zabi Army")
                return await interaction.response.send_message(f"➖ Te quité **{role.name}**.", ephemeral=True)
            await interaction.user.add_roles(role, reason="Self role Zabi Army")
            await interaction.response.send_message(f"➕ Ahora tenés **{role.name}**.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("No puedo administrar ese rol. Revisá la jerarquía del bot.", ephemeral=True)


class RolePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for index, (emoji, label, role_name) in enumerate(SELF_ROLES):
            self.add_item(ToggleRoleButton(emoji, label, role_name, row=index // 4))


# ──────────────────────────────────────────────────────────────────────────────
# SUGERENCIAS
# ──────────────────────────────────────────────────────────────────────────────

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

    @discord.ui.button(label="Enviar sugerencia", emoji="💡", style=discord.ButtonStyle.primary, custom_id="zabi:suggestion:new")
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SuggestionModal())


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
        member_role = find_role(guild, ROLE_MEMBER)
        if member_role is not None and member_role not in interaction.user.roles and not is_staff(interaction.user):
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
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
        }
        if guild.me:
            overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)
        for role in staff_roles(guild):
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        safe_name = re.sub(r"[^a-z0-9-]", "", interaction.user.name.lower().replace(" ", "-"))[:35] or str(interaction.user.id)
        channel = await guild.create_text_channel(
            f"🔒・ticket-{safe_name}",
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

        reports = find_text(guild, CH_REPORTS)
        if reports:
            await reports.send(f"🎫 {interaction.user.mention} abrió {channel.mention}.", allowed_mentions=discord.AllowedMentions.none())


# ──────────────────────────────────────────────────────────────────────────────
# TWITCH CLIPS
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
        params={"client_id": TWITCH_CLIENT_ID, "client_secret": TWITCH_CLIENT_SECRET, "grant_type": "client_credentials"},
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
    view.add_item(discord.ui.Button(
        label="Ver clip",
        emoji="🟣",
        style=discord.ButtonStyle.link,
        url=clip.get("url") or f"https://www.twitch.tv/{TWITCH_CHANNEL}",
    ))
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


# ──────────────────────────────────────────────────────────────────────────────
# INSTALACIÓN DEL SERVIDOR
# ──────────────────────────────────────────────────────────────────────────────

async def ensure_panels(guild: discord.Guild) -> None:
    verify = find_text(guild, CH_VERIFY)
    rules = find_text(guild, CH_RULES)
    roles = find_text(guild, CH_ROLES)
    resources = find_text(guild, CH_RESOURCES)
    suggestions = find_text(guild, CH_SUGGESTIONS)
    tickets = find_text(guild, CH_TICKET_PANEL)

    if verify:
        await ensure_embed_message(
            verify,
            title="😈 Bienvenido/a a Zabi Army",
            description=(
                "Para entrar al resto del servidor, tocá el botón de abajo.\n\n"
                "Al verificarte aceptás respetar las reglas de la comunidad. Después se desbloquean los chats, voz, roles, clips, sugerencias y tickets."
            ),
            colour=discord.Colour.purple(),
            view=VerifyView(),
        )

    if rules:
        await ensure_embed_message(
            rules,
            title="📜 Las reglas del juego",
            description=(
                "**1.** Tratá a todos con respeto. Nada de acoso, discriminación, peleas o toxicidad constante.\n"
                "**2.** Nada de spam, flood, menciones masivas o publicidad sin permiso.\n"
                "**3.** No compartas contenido +18, gore ni material que pueda incomodar al resto.\n"
                "**4.** No publiques información personal propia o ajena.\n"
                "**5.** Usá cada canal para lo que corresponde y respetá las indicaciones del staff.\n"
                "**6.** Las bromas están bien mientras no se conviertan en hostigamiento.\n"
                "**7.** No uses multicuentas para evadir sanciones.\n\n"
                "😈 **La idea es pasarla bien. Si algo perjudica a la comunidad, el staff puede intervenir aunque no esté escrito palabra por palabra acá.**"
            ),
            colour=discord.Colour.dark_purple(),
        )

    if roles:
        await ensure_embed_message(
            roles,
            title="🎭 Elegí tus roles",
            description=(
                "Personalizá tu perfil tocando los botones. Podés elegir varios y volver a tocarlos para quitarlos.\n\n"
                "🔔 Avisos de Zabi\n🔫 Valorant · ⛏️ Minecraft · 🎮 Otros juegos\n🖥️ PC · 🎮 Consola · 📱 Mobile"
            ),
            view=RolePanelView(),
        )

    if resources:
        await ensure_embed_message(
            resources,
            title="🔗 Cosas útiles",
            description=(
                "Acá el staff puede dejar redes, links importantes, comandos, horarios o cualquier recurso útil de Zabi Army."
            ),
        )

    if suggestions:
        await ensure_embed_message(
            suggestions,
            title="💡 Tirate una idea",
            description="¿Se te ocurrió algo para mejorar Zabi Army? Tocá el botón, mandalo y la comunidad puede votar con 👍 o 👎.",
            view=SuggestionPanelView(),
        )

    if tickets:
        await ensure_embed_message(
            tickets,
            title="🎫 Hablá con el staff",
            description="¿Necesitás ayuda, querés reportar algo o hablar en privado? Abrí un ticket y se crea un canal visible solo para vos y el staff.",
            view=TicketPanelView(),
        )


async def install_server(guild: discord.Guild) -> None:
    await ensure_roles(guild)
    await ensure_role_order(guild)

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

    await ensure_text(guild, entry, CH_VERIFY, topic="Verificate para desbloquear Zabi Army.", overwrites=verify_ow)
    await ensure_text(guild, entry, CH_RULES, topic="Reglas y convivencia de Zabi Army.", overwrites=public_ro)
    await ensure_text(guild, entry, CH_ANNOUNCEMENTS, topic="Anuncios oficiales de Zabi Army.", overwrites=public_ro)
    await ensure_text(guild, entry, CH_RESOURCES, topic="Links y recursos útiles.", overwrites=public_ro)
    await ensure_text(guild, entry, CH_ROLES, topic="Elegí juegos, plataformas y avisos.", overwrites=member_ro)

    await ensure_text(guild, community, CH_GENERAL, topic="La charla principal de Zabi Army.", overwrites=member_text)
    await ensure_text(guild, community, CH_WELCOME, topic="Bienvenidas automáticas a nuevos miembros verificados.", overwrites=member_ro)
    await ensure_text(guild, community, CH_DELINQUENTS, topic="El rincón de los delincuentes 😈", overwrites=member_text)
    await ensure_text(guild, community, CH_LATE, topic="Charlas para cuando nadie quiere dormir.", overwrites=member_text)
    await ensure_text(guild, community, CH_MEDIA, topic="Fotos, capturas y pruebas del delito.", overwrites=member_text)
    await ensure_text(guild, community, CH_MEMES, topic="Memes y caos controlado.", overwrites=member_text)
    await ensure_text(guild, community, CH_MUSIC, topic="Pasá temas y playlists.", overwrites=member_text)
    clips = await ensure_text(guild, community, CH_CLIPS, topic="Clips nuevos de Zabi publicados automáticamente.", overwrites=member_ro)
    await ensure_text(guild, community, CH_SUGGESTIONS, topic="Ideas y sugerencias de la comunidad.", overwrites=member_ro)

    await ensure_text(guild, gaming, CH_GAMING, topic="Gaming general.", overwrites=member_text)
    await ensure_text(guild, gaming, CH_VALORANT, topic="Rankeds, Valorant y sufrimiento competitivo.", overwrites=member_text)
    await ensure_text(guild, gaming, CH_LFG, topic="Buscá gente para jugar.", overwrites=member_text)
    await ensure_text(guild, gaming, CH_COMPETITIVE, topic="Competitivo, customs y torneos.", overwrites=member_text)

    await ensure_voice(guild, voice, VC_CONFESSIONAL, member_voice)
    await ensure_voice(guild, voice, VC_HELLFIRE, member_voice)
    await ensure_voice(guild, voice, VC_BASEMENT, member_voice)
    await ensure_voice(guild, voice, VC_INSOMNIA, member_voice)
    await ensure_voice(guild, voice, VC_CREATE, member_voice)

    await ensure_text(guild, tickets, CH_TICKET_PANEL, topic="Abrí un ticket privado con el staff.", overwrites=member_ro)

    await ensure_text(guild, staff, CH_STAFF, topic="Chat privado del staff.", overwrites=staff_ow)
    await ensure_text(guild, staff, CH_REPORTS, topic="Registro de tickets y casos abiertos.", overwrites=staff_ow)
    await ensure_text(guild, staff, CH_LOGS, topic="Entradas, salidas y cambios de roles.", overwrites=staff_ow)

    # El bot siempre conserva permiso de publicación en clips.
    if guild.me:
        clip_ow = clips.overwrites_for(guild.me)
        clip_ow.view_channel = True
        clip_ow.send_messages = True
        clip_ow.embed_links = True
        clip_ow.read_message_history = True
        await clips.set_permissions(guild.me, overwrite=clip_ow, reason="Clips automáticos")

    await ensure_panels(guild)


# ──────────────────────────────────────────────────────────────────────────────
# COMANDOS
# ──────────────────────────────────────────────────────────────────────────────

@bot.tree.command(name="setup", description="Instala o actualiza todo Zabi Army sin borrar canales existentes.")
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
            "✅ **Zabi Army quedó instalado/actualizado.**\n"
            "🎭 Roles · ✅ Verificación · 👋 Bienvenidas · 💬 Canales · 🔊 Voz\n"
            "🎬 Clips · 💡 Sugerencias · 🎫 Tickets · 🛡️ Staff · 📜 Logs\n\n"
            "No borré canales existentes: los conocidos se reutilizan y migran.",
            ephemeral=True,
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Discord bloqueó una acción. El bot necesita **Gestionar canales**, **Gestionar roles** y **Gestionar mensajes**, y su rol debe estar por encima de los roles que administra.",
            ephemeral=True,
        )
    except Exception as exc:
        await interaction.followup.send(f"❌ Error: `{type(exc).__name__}: {str(exc)[:700]}`", ephemeral=True)
        raise


@bot.tree.command(name="actualizar-paneles", description="Actualiza verificación, reglas, roles, sugerencias y tickets.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def update_panels(interaction: discord.Interaction):
    if interaction.guild is None or not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await ensure_panels(interaction.guild)
        await interaction.followup.send("✅ Paneles y mensajes actualizados.", ephemeral=True)
    except Exception as exc:
        await interaction.followup.send(f"❌ `{type(exc).__name__}: {str(exc)[:600]}`", ephemeral=True)


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


@bot.tree.command(name="bot-estado", description="Muestra el estado del Zabi Army Bot.")
@app_commands.guild_only()
async def bot_status(interaction: discord.Interaction):
    twitch = f"✅ @{TWITCH_CHANNEL}" if TWITCH_ENABLED else "❌ sin configurar"
    member_role = find_role(interaction.guild, ROLE_MEMBER) if interaction.guild else None
    verify_channel = find_text(interaction.guild, CH_VERIFY) if interaction.guild else None
    await interaction.response.send_message(
        "🤖 **Zabi Army Bot**\n"
        f"🎬 Twitch: {twitch}\n"
        f"✅ Verificación: {'✅' if member_role and verify_channel else '❌'}\n"
        "🎭 Roles: ✅\n💡 Sugerencias: ✅\n🎫 Tickets: ✅",
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


# ──────────────────────────────────────────────────────────────────────────────
# LOGS BÁSICOS
# ──────────────────────────────────────────────────────────────────────────────

async def send_log(guild: discord.Guild, text: str) -> None:
    channel = find_text(guild, CH_LOGS)
    if channel:
        try:
            await channel.send(text, allowed_mentions=discord.AllowedMentions.none())
        except discord.Forbidden:
            pass


@bot.event
async def on_member_join(member: discord.Member):
    await send_log(member.guild, f"📥 Entró **{member}** (`{member.id}`). Esperando verificación.")


@bot.event
async def on_member_remove(member: discord.Member):
    await send_log(member.guild, f"📤 Salió **{member}** (`{member.id}`).")


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    before_ids = {role.id for role in before.roles}
    after_ids = {role.id for role in after.roles}
    if before_ids == after_ids:
        return
    added = [role.name for role in after.roles if role.id not in before_ids and role != after.guild.default_role]
    removed = [role.name for role in before.roles if role.id not in after_ids and role != after.guild.default_role]
    parts = []
    if added:
        parts.append("➕ " + ", ".join(added))
    if removed:
        parts.append("➖ " + ", ".join(removed))
    if parts:
        await send_log(after.guild, f"🎭 Roles de **{after}**: " + " | ".join(parts))


# ──────────────────────────────────────────────────────────────────────────────
# HEALTH + ARRANQUE
# ──────────────────────────────────────────────────────────────────────────────

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
        except discord.Forbidden:
            print("ℹ️ El bot todavía no tiene acceso al GUILD_ID configurado; los comandos se sincronizarán cuando esté invitado.")
        except Exception as exc:
            print(f"⚠️ Error sincronizando comandos: {exc}")

    if TWITCH_ENABLED and not clips_watch.is_running():
        clips_watch.start()
        print(f"🎬 Twitch clips activo: @{TWITCH_CHANNEL} cada {TWITCH_CLIPS_POLL_SECONDS}s")


async def main():
    if not TOKEN:
        raise RuntimeError("Falta DISCORD_TOKEN")
    bot.add_view(VerifyView())
    bot.add_view(RolePanelView())
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
