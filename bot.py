import os
import discord
from discord import Interaction, app_commands
from dotenv import load_dotenv

from CONSTANTS import ADMINS, GUILDS
import election_manager as em


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
# intents.message_content = True
bot = discord.Client(intents=intents)
commands = app_commands.CommandTree(bot)


@commands.command(name="join_race", description="Add yourself as a candidate.", guilds=GUILDS)
async def add_candidate(interaction: Interaction):
    guild_id = interaction.guild_id
    user_id = interaction.user.id
    message = em.add_candidate(discord.Object(id=guild_id), user_id)
    await interaction.response.send_message(message)


@commands.command(name="leave_race", description="Remove yourself as a candidate.", guilds=GUILDS)
async def remove_candidate(interaction: Interaction):
    guild_id = interaction.guild_id
    user_id = interaction.user.id
    message = em.remove_candidate(discord.Object(id=guild_id), user_id)
    await interaction.response.send_message(message)


@commands.command(
    name="list_candidates",
    description="List the candidates currently in the election.",
    guilds=GUILDS,
)
async def list_candidates(interaction: Interaction):
    guild_id = interaction.guild_id
    message = em.get_candidate_list(discord.Object(id=guild_id))
    await interaction.response.send_message(message)


@commands.command(
    name="run_election",
    description="Run the election.",
    guilds=GUILDS,
)
async def run_election(interaction: Interaction):
    guild_id = interaction.guild_id
    user_id = interaction.user.id

    if user_id not in ADMINS:
        await interaction.response.send_message("You are not part of the I.O.C.")

    message = em.start_election(discord.Object(id=guild_id))
    await interaction.response.send_message(message)


@bot.event
async def on_ready():
    for guild in GUILDS:
        await commands.sync(guild=guild)


bot.run(TOKEN)
