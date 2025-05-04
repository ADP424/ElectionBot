import discord


candidates: dict[discord.Object, list[int]] = {}  # lists of Discord ids per server
election_running: dict[discord.Object, bool] = {}


def add_candidate(guild: discord.Object, discord_id: int):
    if not election_running.get(guild, False):
        election_running[guild] = False
    if not election_running[guild]:
        return "There isn't currently an election to join."

    if not candidates.get(guild, False):
        candidates[guild] = []
    if discord_id in candidates[guild]:
        return "You're already in the election."

    candidates[guild].append(discord_id)
    return "You added yourself to the election."


def remove_candidate(guild: discord.Object, discord_id: int):
    if not election_running.get(guild, False):
        election_running[guild] = False
    if not election_running[guild]:
        return "There isn't currently an election to leave."

    if not candidates.get(guild, False):
        candidates[guild] = []
    if discord_id not in candidates[guild]:
        return "You're already not in the election."

    candidates[guild].remove(discord_id)
    return "You removed yourself from the election."


def get_candidate_list(guild: discord.Object):
    if not election_running.get(guild, False):
        election_running[guild] = False
    if not election_running[guild]:
        return "There isn't currently an election."

    if not candidates.get(guild, False) or len(candidates[guild]) == 0:
        return "No candidates have joined so far."

    message = ""
    for candidate in candidates[guild]:
        message += f"<@{candidate}>\n"

    return message


def start_election(guild: discord.Object):
    election_running[guild] = True
    return "Successfully started an election!"
