from __future__ import annotations

import discord


def install(base) -> None:
    """Hace que una búsqueda /party se elimine al cerrarse."""

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

            # Confirmación privada para quien cerró el party y eliminación inmediata
            # del mensaje público para que no queden búsquedas viejas en el canal.
            await interaction.response.send_message(
                "✅ Party cerrado y eliminado.", ephemeral=True
            )
            try:
                await interaction.message.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

    # /party y main() consultan este global al ejecutarse, así que reemplazarlo acá
    # conserva el resto de la lógica y también registra la vista persistente nueva.
    base.PartyView = PartyView
