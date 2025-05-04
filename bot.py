import datetime
from discord.ext import tasks
import os
import discord
from discord import Interaction, app_commands
from discord.ui import View, Button
from dotenv import load_dotenv

from CONSTANTS import ADMINS, GUILDS, OUTPUT_CHANNEL
import election_manager as em

should_end_election = False


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
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
    message, _ = em.get_candidate_list(discord.Object(id=guild_id))
    await interaction.response.send_message(message)


@commands.command(
    name="run_election",
    description="Run the election.",
    guilds=GUILDS,
)
async def run_election(interaction: Interaction):

    @tasks.loop(time=datetime.time(hour=0, minute=0), count=2)
    async def on_election_end():
        global should_end_election
        if should_end_election:
            for guild in GUILDS:
                message, _ = em.end_election(guild)
                await bot.get_channel(OUTPUT_CHANNEL).send(message)
        should_end_election = True

    @tasks.loop(minutes=1, count=2)
    async def on_election_end_dev():
        global should_end_election
        if should_end_election:
            for guild in GUILDS:
                message, _ = em.end_election(guild)
                await bot.get_channel(OUTPUT_CHANNEL).send(message)
        should_end_election = True

    guild_id = interaction.guild_id
    user_id = interaction.user.id

    if user_id not in ADMINS:
        await interaction.response.send_message("You are not part of the I.O.C.")
        return

    message, success = em.start_election(discord.Object(id=guild_id))
    if success:
        global should_end_election
        should_end_election = False
        on_election_end_dev.start()
    await interaction.response.send_message(message)


@commands.command(
    name="vote",
    description="Vote in the election.",
    guilds=GUILDS,
)
async def vote(interaction: Interaction):
    guild_id = interaction.guild_id
    user_id = interaction.user.id

    # if user_id in ADMINS:
    #     await interaction.response.send_message("Members of the I.O.C. cannot vote for the C.R.P.", ephemeral=True)
    #     return

    if em.citizen_has_voted(discord.Object(id=guild_id), user_id):
        await interaction.response.send_message("You already voted!", ephemeral=True)
        return

    message, candidates = em.get_candidate_list(discord.Object(id=guild_id))

    async def update_message():
        view = View()

        async def load_candidate_buttons():

            for candidate_id in candidates:
                candidate = await bot.fetch_user(candidate_id)
                button = Button(label=f"{candidate.global_name} 🗳️", style=discord.ButtonStyle.primary)

                async def button_callback(interaction: Interaction, candidate_id=candidate_id):
                    candidates.remove(candidate_id)
                    message = em.add_ranked_vote(discord.Object(id=guild_id), user_id, candidate_id)
                    await interaction.response.send_message(message, ephemeral=True)
                    await update_message()

                button.callback = button_callback
                view.add_item(button)

        await load_candidate_buttons()
        if interaction.response.is_done():
            await interaction.edit_original_response(content=message, view=view)
        else:
            await interaction.response.send_message(message, view=view, ephemeral=True)

    await update_message()


@bot.event
async def on_ready():
    for guild in GUILDS:
        await commands.sync(guild=guild)


bot.run(TOKEN)
