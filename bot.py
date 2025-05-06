import datetime
from discord.ext import tasks
import os
import discord
from discord import AllowedMentions, Interaction, app_commands
from discord.ui import View, Button
from dotenv import load_dotenv

from CONSTANTS import ADMINS, GUILDS, OUTPUT_CHANNEL
import election_manager as em


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

STAGE = "dev"  # bot behaves differently if I'm testing

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
commands = app_commands.CommandTree(bot)

should_end_election: dict[discord.Object, bool] = {}


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


async def _end_election(guild: discord.Object):
    message, _ = em.end_election(guild)
    await bot.get_channel(OUTPUT_CHANNEL[guild]).send(message)


@commands.command(
    name="run_election",
    description="Run the election.",
    guilds=GUILDS,
)
async def run_election(interaction: Interaction):
    guild_id = interaction.guild_id
    user_id = interaction.user.id

    @tasks.loop(time=datetime.time(hour=0, minute=0), count=2)
    async def on_election_end():
        global should_end_election
        if should_end_election.get(discord.Object(id=guild_id), False):
            await _end_election(discord.Object(id=guild_id))
            print(f"Ended election for server {guild_id}")
        should_end_election[discord.Object(id=guild_id)] = True

    @tasks.loop(minutes=15, count=2)
    async def on_election_end_dev():
        global should_end_election
        if should_end_election.get(discord.Object(id=guild_id), False):
            await _end_election(discord.Object(id=guild_id))
            print(f"Ended election for server {guild_id}")
        should_end_election[discord.Object(id=guild_id)] = True

    if user_id not in ADMINS and STAGE != "dev":
        await interaction.response.send_message("You are not part of the I.O.C.")
        return

    message, success = em.start_election(discord.Object(id=guild_id))
    if success:
        global should_end_election
        should_end_election[discord.Object(id=guild_id)] = False

        print(f"Started election for server {guild_id}")
        if STAGE != "dev":
            on_election_end.start()
        else:
            on_election_end_dev.start()
    await interaction.response.send_message(message)


@commands.command(
    name="end_election",
    description="End the election early.",
    guilds=GUILDS,
)
async def end_election(interaction: Interaction):
    guild_id = interaction.guild_id
    user_id = interaction.user.id

    if user_id not in ADMINS and STAGE != "dev":
        await interaction.response.send_message("You are not part of the I.O.C.")
        return

    await _end_election(discord.Object(id=guild_id))
    await interaction.response.send_message("Ended the election.")


@commands.command(
    name="vote",
    description="Vote in the election.",
    guilds=GUILDS,
)
async def vote(interaction: Interaction):
    guild_id = interaction.guild_id
    user_id = interaction.user.id

    if user_id in ADMINS and STAGE != "dev":
        await interaction.response.send_message("Members of the I.O.C. cannot vote for the C.R.P.", ephemeral=True)
        return

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


@commands.command(
    name="clear_election",
    description="Clear all candidates and votes.",
    guilds=GUILDS,
)
async def clear_election(interaction: Interaction):
    guild_id = interaction.guild_id
    user_id = interaction.user.id

    if user_id not in ADMINS and STAGE != "dev":
        await interaction.response.send_message("You are not part of the I.O.C.")
        return

    message, _ = em.end_election(discord.Object(id=guild_id))
    await interaction.response.send_message(message)


@commands.command(
    name="list_candidates",
    description="List the candidates currently in the election.",
    guilds=GUILDS,
)
async def list_candidates(interaction: Interaction):
    guild_id = interaction.guild_id
    message, _ = em.get_candidate_list(discord.Object(id=guild_id))
    await interaction.response.send_message(message, allowed_mentions=AllowedMentions(users=False))


@bot.event
async def on_ready():
    for guild in GUILDS:
        await commands.sync(guild=guild)


bot.run(TOKEN)
