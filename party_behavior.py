from __future__ import annotations

import discord
from discord import app_commands


PARTY_MODE_CHOICES = [
    app_commands.Choice(name="Competitivo", value="Competitivo"),
    app_commands.Choice(name="Swiftplay", value="Swiftplay"),
    app_commands.Choice(name="Normal / Unrated", value="Normal / Unrated"),
    app_commands.Choice(name="Spike Rush", value="Spike Rush"),
    app_commands.Choice(name="Premier", value="Premier"),
    app_commands.Choice(name="Deathmatch", value="Deathmatch"),
    app_commands.Choice(name="Team Deathmatch", value="Team Deathmatch"),
    app_commands.Choice(name="Escalation", value="Escalation"),
    app_commands.Choice(name="Custom / Personalizada", value="Custom / Personalizada"),
]


def install(base) -> None:
    """Mejora /party: modos seleccionables y eliminación de la búsqueda al cerrarla."""

    class PartyView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(
            label="Unirme",
            emoji="✅",
            style=discord.ButtonStyle.success,
            custom_id="zabi:party:join",
        )
        async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
            if (
                interaction.message is None
                or not interaction.message.embeds
                or not isinstance(interaction.user, discord.Member)
            ):
                return

            embed = interaction.message.embeds[0].copy()
            state = base.parse_party_footer(embed)
            if state is None:
                return await interaction.response.send_message(
                    "No pude leer esta búsqueda.", ephemeral=True
                )

            owner_id, max_players, closed = state
            members = base.parse_party_members(embed)
            if closed:
                return await interaction.response.send_message(
                    "Esta búsqueda está cerrada.", ephemeral=True
                )
            if interaction.user.id in members:
                return await interaction.response.send_message(
                    "Ya estás en el grupo.", ephemeral=True
                )
            if len(members) >= max_players:
                return await interaction.response.send_message(
                    "El grupo ya está completo.", ephemeral=True
                )

            members.append(interaction.user.id)
            base.set_party_members(embed, members, max_players)
            if len(members) >= max_players:
                embed.title = "✅ Grupo completo — Valorant"
                embed.colour = discord.Colour.green()

            await interaction.response.edit_message(embed=embed, view=PartyView())

        @discord.ui.button(
            label="Salir",
            emoji="🚪",
            style=discord.ButtonStyle.secondary,
            custom_id="zabi:party:leave",
        )
        async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
            if (
                interaction.message is None
                or not interaction.message.embeds
                or not isinstance(interaction.user, discord.Member)
            ):
                return

            embed = interaction.message.embeds[0].copy()
            state = base.parse_party_footer(embed)
            if state is None:
                return await interaction.response.send_message(
                    "No pude leer esta búsqueda.", ephemeral=True
                )

            owner_id, max_players, _closed = state
            members = base.parse_party_members(embed)
            if interaction.user.id == owner_id:
                return await interaction.response.send_message(
                    "Si sos quien creó el grupo, usá **Cerrar**.", ephemeral=True
                )
            if interaction.user.id not in members:
                return await interaction.response.send_message(
                    "No estabas en el grupo.", ephemeral=True
                )

            members.remove(interaction.user.id)
            base.set_party_members(embed, members, max_players)
            embed.title = "👥 Buscando gente — Valorant"
            embed.colour = discord.Colour.blurple()
            await interaction.response.edit_message(embed=embed, view=PartyView())

        @discord.ui.button(
            label="Cerrar",
            emoji="🔒",
            style=discord.ButtonStyle.danger,
            custom_id="zabi:party:close",
        )
        async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
            if (
                interaction.message is None
                or not interaction.message.embeds
                or not isinstance(interaction.user, discord.Member)
            ):
                return

            state = base.parse_party_footer(interaction.message.embeds[0])
            if state is None:
                return await interaction.response.send_message(
                    "No pude leer esta búsqueda.", ephemeral=True
                )

            owner_id, _max_players, _closed = state
            if interaction.user.id != owner_id and not base.is_staff(interaction.user):
                return await interaction.response.send_message(
                    "Solo quien creó la búsqueda o el staff puede cerrarla.",
                    ephemeral=True,
                )

            await interaction.response.send_message(
                "✅ Party cerrado y eliminado.", ephemeral=True
            )
            try:
                await interaction.message.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

    base.PartyView = PartyView

    # El /party original usa `modo: str`, por eso Discord mostraba un campo de texto.
    # Lo reemplazamos antes de sincronizar los slash commands y agregamos choices.
    base.bot.tree.remove_command("party")

    @base.bot.tree.command(name="party", description="Buscá gente para jugar Valorant.")
    @app_commands.guild_only()
    @app_commands.describe(
        modo="Modo de juego",
        cupos="Cantidad total de jugadores (2 a 5)",
        servidor="Servidor o región",
    )
    @app_commands.choices(modo=PARTY_MODE_CHOICES)
    async def party(
        interaction: discord.Interaction,
        modo: app_commands.Choice[str],
        cupos: app_commands.Range[int, 2, 5] = 5,
        servidor: str = "No especificado",
    ):
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            return

        channel = base.find_text(interaction.guild, base.CH_LFG)
        if channel is None:
            return await interaction.response.send_message(
                "No encuentro el canal para buscar gente.", ephemeral=True
            )
        if interaction.channel_id != channel.id:
            return await interaction.response.send_message(
                f"Usá `/party` dentro de {channel.mention}.", ephemeral=True
            )

        member_role = base.find_role(interaction.guild, base.ROLE_MEMBER)
        if (
            member_role
            and member_role not in interaction.user.roles
            and not base.is_staff(interaction.user)
        ):
            return await interaction.response.send_message(
                "Primero verificáte.", ephemeral=True
            )

        mode_value = modo.value
        embed = discord.Embed(
            title="👥 Buscando gente — Valorant",
            description=f"**{interaction.user.display_name}** está armando grupo.",
            colour=discord.Colour.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="🎯 Modo", value=base.safe_text(mode_value, 80), inline=True)
        embed.add_field(
            name="🏅 Rango",
            value=base.get_member_valorant_rank(interaction.user),
            inline=True,
        )
        embed.add_field(
            name="🌐 Servidor",
            value=base.safe_text(servidor, 80),
            inline=True,
        )
        embed.add_field(
            name="👥 Jugadores",
            value=f"{interaction.user.mention}\n\n**1/{cupos}**",
            inline=False,
        )
        embed.set_footer(
            text=f"party_owner:{interaction.user.id}|max:{cupos}|closed:0"
        )
        await interaction.response.send_message(
            embed=embed,
            view=PartyView(),
            allowed_mentions=discord.AllowedMentions.none(),
        )
