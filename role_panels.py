from __future__ import annotations

from typing import Optional

import discord


AGE_REACTION_ROLES = {
    "🧒": "🧒・Menor de 18",
    "🎂": "🎂・18-25",
    "🧑": "🧑・26+",
}

VALORANT_CUSTOM_EMOJIS = {
    "⚫・Sin rango": None,
    "⬛・Hierro": "valoranthierro",
    "🟫・Bronce": "valorantbronce",
    "⬜・Plata": "valorantplata",
    "🟨・Oro": "valorantoro",
    "🟩・Platino": "valorantplatino",
    "💎・Diamante": "valorantdiamante",
    "🟪・Ascendente": "valorantascendente",
    "🟥・Inmortal": "valorantimmortal",
    "🌟・Radiante": "valorantradiante",
}

ROLE_PANEL_COUNTRY_TITLE = "🌎 Elegí tu país"
ROLE_PANEL_AGE_TITLE = "🎂 Elegí tu rango de edad"
ROLE_PANEL_RANK_TITLE = "🔫 Elegí tu rango de Valorant"
ROLE_PANEL_GAMES_TITLE = "🎮 Elegí tus juegos"
ROLE_PANEL_PLATFORM_TITLE = "🖥️ Elegí tus plataformas"
ROLE_PANEL_NOTIFY_TITLE = "📣 Elegí tus avisos"


def install(base) -> None:
    """Instala en Zabi Army el mismo estilo de roles por reacción que Softblade."""

    country_reaction_roles = {
        name.split("・", 1)[0]: name
        for name in base.COUNTRIES
    }
    game_reaction_roles = {
        "🔫": base.ROLE_GAME_VALORANT,
        "⛏️": base.ROLE_GAME_MINECRAFT,
        "🎮": base.ROLE_GAME_OTHER,
    }
    platform_reaction_roles = {
        "🖥️": base.ROLE_PLATFORM_PC,
        "🎮": base.ROLE_PLATFORM_CONSOLE,
        "📱": base.ROLE_PLATFORM_MOBILE,
    }
    notify_reaction_roles = {
        "🔔": base.ROLE_LIVE_NOTIFY,
        "🎉": base.ROLE_EVENT_NOTIFY,
    }

    def build_rank_reaction_roles(guild: discord.Guild) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for role_name in base.VALORANT_RANKS:
            emoji_name = VALORANT_CUSTOM_EMOJIS.get(role_name)
            if emoji_name:
                custom_emoji = discord.utils.get(guild.emojis, name=emoji_name)
                if custom_emoji is not None:
                    mapping[str(custom_emoji)] = role_name
                    continue
            mapping[role_name.split("・", 1)[0]] = role_name
        return mapping

    def role_panel_line(guild: discord.Guild, emoji: str, role_name: str) -> str:
        role = base.find_role(guild, role_name)
        label = role.mention if role is not None else f"**{role_name.split('・', 1)[-1]}**"
        return f"{emoji} ─ {label}"

    async def ensure_reaction_role_panel(
        channel: discord.TextChannel,
        title: str,
        description: str,
        mapping: dict[str, str],
    ) -> discord.Message:
        matches = await base.bot_embed_messages(channel, title, limit=500)
        embed = discord.Embed(
            title=title,
            description=description,
            colour=discord.Colour.blurple(),
        )
        embed.set_footer(
            text="Reaccioná para asignarte el rol • Quitá tu reacción para quitarlo"
        )

        if matches:
            message = matches[0]
            try:
                await message.edit(
                    embed=embed,
                    view=None,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                pass
            for duplicate in matches[1:]:
                try:
                    await duplicate.delete()
                except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                    pass
        else:
            message = await channel.send(
                embed=embed,
                allowed_mentions=discord.AllowedMentions.none(),
            )

        wanted = set(mapping.keys())
        for reaction in list(message.reactions):
            if str(reaction.emoji) not in wanted:
                try:
                    await message.clear_reaction(reaction.emoji)
                except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                    pass

        try:
            message = await channel.fetch_message(message.id)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass

        existing = {str(reaction.emoji) for reaction in message.reactions}
        for emoji in mapping:
            if emoji in existing:
                continue
            try:
                reaction_emoji = (
                    discord.PartialEmoji.from_str(emoji)
                    if emoji.startswith("<")
                    else emoji
                )
                await message.add_reaction(reaction_emoji)
                existing.add(emoji)
            except (
                discord.Forbidden,
                discord.NotFound,
                discord.HTTPException,
                ValueError,
            ):
                pass

        return message

    async def ensure_role_reaction_panels(
        guild: discord.Guild,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        channel = channel or base.find_text(guild, base.CH_ROLES)
        if channel is None:
            return

        # Softblade no usa un selector único: usa seis paneles separados por reacción.
        old_titles = {
            "🎭 Elegí tus roles",
            "🌎 Roles de perfil",
            f"{base.GUIDE_PREFIX}Roles",
        }
        try:
            async for message in channel.history(limit=300):
                if (
                    message.author == guild.me
                    and message.embeds
                    and message.embeds[0].title in old_titles
                ):
                    try:
                        await message.delete()
                    except (
                        discord.Forbidden,
                        discord.NotFound,
                        discord.HTTPException,
                    ):
                        pass
        except (discord.Forbidden, discord.HTTPException):
            pass

        country_lines = "\n".join(
            role_panel_line(guild, emoji, role_name)
            for emoji, role_name in country_reaction_roles.items()
        )
        await ensure_reaction_role_panel(
            channel,
            ROLE_PANEL_COUNTRY_TITLE,
            "↳ **Seleccioná tu nacionalidad.**\n\n"
            + country_lines
            + "\n\nSolo podés tener **un país** a la vez. Si reaccionás a otro, el bot reemplaza el anterior.",
            country_reaction_roles,
        )

        age_lines = "\n".join(
            role_panel_line(guild, emoji, role_name)
            for emoji, role_name in AGE_REACTION_ROLES.items()
        )
        await ensure_reaction_role_panel(
            channel,
            ROLE_PANEL_AGE_TITLE,
            "↳ **Seleccioná tu rango de edad.** No hace falta decir tu edad exacta.\n\n"
            + age_lines
            + "\n\nSolo podés tener **un rango de edad** a la vez; si cambiás, se reemplaza el anterior.",
            AGE_REACTION_ROLES,
        )

        rank_mapping = build_rank_reaction_roles(guild)
        rank_lines = "\n".join(
            role_panel_line(guild, emoji, role_name)
            for emoji, role_name in rank_mapping.items()
        )
        await ensure_reaction_role_panel(
            channel,
            ROLE_PANEL_RANK_TITLE,
            "↳ **Seleccioná tu rango actual.**\n\n"
            + rank_lines
            + "\n\nSolo podés tener **un rango** a la vez; si cambiás, se reemplaza el anterior.",
            rank_mapping,
        )

        game_lines = "\n".join(
            role_panel_line(guild, emoji, role_name)
            for emoji, role_name in game_reaction_roles.items()
        )
        await ensure_reaction_role_panel(
            channel,
            ROLE_PANEL_GAMES_TITLE,
            "↳ **Elegí los juegos que te interesan.** Podés marcar varios.\n\n"
            + game_lines,
            game_reaction_roles,
        )

        platform_lines = "\n".join(
            role_panel_line(guild, emoji, role_name)
            for emoji, role_name in platform_reaction_roles.items()
        )
        await ensure_reaction_role_panel(
            channel,
            ROLE_PANEL_PLATFORM_TITLE,
            "↳ **Elegí dónde jugás.** Podés marcar varias plataformas.\n\n"
            + platform_lines,
            platform_reaction_roles,
        )

        notify_lines = "\n".join(
            role_panel_line(guild, emoji, role_name)
            for emoji, role_name in notify_reaction_roles.items()
        )
        await ensure_reaction_role_panel(
            channel,
            ROLE_PANEL_NOTIFY_TITLE,
            "↳ **Elegí qué avisos querés recibir.** Podés marcar más de uno.\n\n"
            + notify_lines
            + "\n\nQuitá una reacción cuando quieras dejar de recibir ese aviso.",
            notify_reaction_roles,
        )

    async def get_reaction_panel_mapping(payload: discord.RawReactionActionEvent):
        guild = base.bot.get_guild(payload.guild_id) if payload.guild_id else None
        if guild is None:
            return None, None, None, False

        channel = guild.get_channel(payload.channel_id)
        roles_channel = base.find_text(guild, base.CH_ROLES)
        if (
            not isinstance(channel, discord.TextChannel)
            or roles_channel is None
            or channel.id != roles_channel.id
        ):
            return guild, None, None, False

        try:
            message = await channel.fetch_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return guild, None, None, False

        if not message.embeds:
            return guild, message, None, False

        title = message.embeds[0].title
        if title == ROLE_PANEL_COUNTRY_TITLE:
            return guild, message, country_reaction_roles, True
        if title == ROLE_PANEL_AGE_TITLE:
            return guild, message, AGE_REACTION_ROLES, True
        if title == ROLE_PANEL_RANK_TITLE:
            return guild, message, build_rank_reaction_roles(guild), True
        if title == ROLE_PANEL_GAMES_TITLE:
            return guild, message, game_reaction_roles, False
        if title == ROLE_PANEL_PLATFORM_TITLE:
            return guild, message, platform_reaction_roles, False
        if title == ROLE_PANEL_NOTIFY_TITLE:
            return guild, message, notify_reaction_roles, False
        return guild, message, None, False

    async def reaction_member(
        guild: discord.Guild,
        user_id: int,
    ) -> Optional[discord.Member]:
        member = guild.get_member(user_id)
        if member is not None:
            return member
        try:
            return await guild.fetch_member(user_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    original_ensure_panels = base.ensure_panels
    original_ensure_guides = base.ensure_guides

    async def patched_ensure_panels(guild: discord.Guild) -> None:
        # Conserva verificación, reglas, sugerencias y tickets existentes.
        await original_ensure_panels(guild)
        # Después reemplaza únicamente el panel viejo de roles por el sistema Softblade.
        await ensure_role_reaction_panels(guild)

    async def patched_ensure_guides(guild: discord.Guild):
        result = await original_ensure_guides(guild)
        roles_channel = base.find_text(guild, base.CH_ROLES)
        if roles_channel is not None:
            guide_title = f"{base.GUIDE_PREFIX}Roles"
            matches = await base.bot_embed_messages(
                roles_channel,
                guide_title,
                limit=300,
            )
            for message in matches:
                try:
                    await message.delete()
                except (
                    discord.Forbidden,
                    discord.NotFound,
                    discord.HTTPException,
                ):
                    pass
        return result

    # Las funciones ya registradas de /setup, /actualizar-roles, /actualizar-paneles
    # y /actualizar-guias consultan estos globals en tiempo de ejecución.
    base.ensure_panels = patched_ensure_panels
    base.ensure_guides = patched_ensure_guides
    base.ensure_role_reaction_panels = ensure_role_reaction_panels

    @base.bot.event
    async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
        if (
            base.bot.user is None
            or payload.user_id == base.bot.user.id
            or payload.guild_id is None
        ):
            return

        # Conserva las votaciones de sugerencias del bot de Zabi.
        await base.handle_suggestion_reaction(payload, True)

        guild, message, mapping, exclusive = await get_reaction_panel_mapping(payload)
        if guild is None or message is None or mapping is None:
            return

        emoji = str(payload.emoji)
        role_name = mapping.get(emoji)
        if role_name is None:
            return

        member = await reaction_member(guild, payload.user_id)
        if member is None or member.bot:
            return

        selected = base.find_role(guild, role_name)
        if selected is None:
            return

        group_role_names = set(mapping.values())
        old_roles = (
            [
                role
                for role in member.roles
                if role.name in group_role_names and role != selected
            ]
            if exclusive
            else []
        )

        try:
            if old_roles:
                await member.remove_roles(
                    *old_roles,
                    reason="Cambio de reaction role visual",
                )
            if selected not in member.roles:
                await member.add_roles(selected, reason="Reaction role visual")
        except discord.Forbidden:
            return

        # País, edad y rango son exclusivos; lo demás permite varias opciones.
        if exclusive:
            for reaction in message.reactions:
                reaction_emoji = str(reaction.emoji)
                if reaction_emoji in mapping and reaction_emoji != emoji:
                    try:
                        await reaction.remove(member)
                    except (discord.Forbidden, discord.HTTPException):
                        pass

    @base.bot.event
    async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
        if (
            base.bot.user is None
            or payload.user_id == base.bot.user.id
            or payload.guild_id is None
        ):
            return

        await base.handle_suggestion_reaction(payload, False)

        guild, _message, mapping, _exclusive = await get_reaction_panel_mapping(payload)
        if guild is None or mapping is None:
            return

        role_name = mapping.get(str(payload.emoji))
        if role_name is None:
            return

        member = await reaction_member(guild, payload.user_id)
        role = base.find_role(guild, role_name)
        if member is None or role is None or role not in member.roles:
            return

        try:
            await member.remove_roles(role, reason="Reaction role retirada")
        except discord.Forbidden:
            pass
