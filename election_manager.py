import collections
from copy import copy
import discord

from CONSTANTS import SEATS_AVAILABLE


candidates: dict[discord.Object, list[int]] = {}
election_is_running: dict[discord.Object, bool] = {}
voters: dict[discord.Object, dict[int, list[int]]] = {}
citizen_voted: dict[discord.Object, dict[int, bool]] = {}


def add_candidate(guild: discord.Object, discord_id: int):
    if not candidates.get(guild, False):
        candidates[guild] = []
    if discord_id in candidates[guild]:
        return "You're already in the election."

    if election_is_running.get(guild, False):
        return "You can't join while an election is running."

    candidates[guild].append(discord_id)
    return "You added yourself to the election."


def remove_candidate(guild: discord.Object, discord_id: int):
    if not candidates.get(guild, False):
        candidates[guild] = []
    if discord_id not in candidates[guild]:
        return "You're already not in the election."

    if election_is_running.get(guild, False):
        return "You can't leave while an election is running."

    candidates[guild].remove(discord_id)
    return "You removed yourself from the election."


def clear_election(guild: discord.Object):
    if election_is_running.get(guild, False):
        return "You need to end the current election before you can clear it."

    if not candidates.get(guild, False):
        candidates[guild] = []
    candidates[guild].clear()

    if not voters.get(guild, False):
        voters[guild] = {}
    voters[guild].clear()

    if not citizen_voted.get(guild, False):
        citizen_voted[guild] = {}
    citizen_voted[guild].clear()

    return "All candidates and voters cleared."


def get_candidate_list(guild: discord.Object) -> tuple[str, list[int]]:
    if not candidates.get(guild, False) or len(candidates[guild]) == 0:
        return "No candidates have joined so far.", []

    message = ""
    for candidate in candidates[guild]:
        message += f"<@{candidate}>\n"

    return message, copy(candidates[guild])


def start_election(guild: discord.Object) -> tuple[str, bool]:
    if election_is_running.get(guild, False):
        return "There's already an election running.", False

    election_is_running[guild] = True
    return "Successfully started an election!", True


def end_election(guild: discord.Object) -> tuple[str, bool | list[int]]:
    if not election_is_running.get(guild, False):
        return "There's no election running.", False

    if not candidates.get(guild, False):
        return "No candidates entered this race. So, uh...", False

    if not voters.get(guild, False):
        return "Nobody voted in this race. So, uh...", False

    election_is_running[guild] = False
    message, results = _run_ranked_choice_election(candidates[guild], voters[guild], SEATS_AVAILABLE)

    return message, results


def add_ranked_vote(guild: discord.Object, discord_id: int, candidate_id: int):
    if not voters.get(guild, False):
        voters[guild] = {}

    if not voters[guild].get(discord_id, False):
        voters[guild][discord_id] = []

    voters[guild][discord_id].append(candidate_id)

    if not citizen_voted.get(guild, False):
        citizen_voted[guild] = {}

    citizen_voted[guild][discord_id] = True
    return f"Added that candidate as your Number {len(voters[guild][discord_id])} pick."


def citizen_has_voted(guild: discord.Object, discord_id: int):
    if not citizen_voted.get(guild, False) or not citizen_voted[guild].get(discord_id, False):
        return False
    return True


def _run_ranked_choice_election(
    candidates: list[int], voters: dict[int, list[int]], available_seats: int = SEATS_AVAILABLE
) -> tuple[str, list[int]]:
    result_message = "-------- RESULTS --------\n"

    elected: list[int] = []
    eliminated: set[int] = set()
    all_candidates: set[int] = set(candidates)
    num_voters: int = len(voters)

    quota = num_voters // (num_voters + 1) + 1
    ballots = list(voters.values())
    weights = [1.0] * len(ballots)

    curr_round = 1
    while len(elected) < available_seats and len(all_candidates - set(elected) - eliminated) > 0:
        result_message += f"\n--- Round {curr_round} ---\n"

        # first choice
        tally: dict[int, float] = collections.defaultdict(float)
        for i, ballot in enumerate(ballots):
            for choice in ballot:
                if choice not in eliminated and choice not in elected:
                    tally[choice] += weights[i]
                    break

        result_message += "Tally:\n"
        for candidate, num_votes in tally.items():
            result_message += f"\t<@{candidate}> : {num_votes} votes\n"
        result_message += "\n"

        # elect any candidate that meets the quota
        newly_elected: list[int] = []
        for candidate, votes in tally.items():
            if votes >= quota and candidate not in elected:
                elected.append(candidate)
                newly_elected.append(candidate)
                result_message += f"<@{candidate}> elected with {votes} votes!\n"

        # transfer excess votes from elected candidates
        for candidate in newly_elected:
            surplus = tally[candidate] - quota
            if surplus <= 0:
                continue

            total_transferable = 0
            for i, ballot in enumerate(ballots):
                if ballot[0] == candidate:
                    total_transferable += weights[i]

            if total_transferable == 0:
                continue

            transfer_ratio = surplus / total_transferable
            for i, ballot in enumerate(ballots):
                if ballot[0] == candidate:
                    weights[i] *= transfer_ratio
                    ballots[i] = [c for c in ballot if c != candidate]

        if not newly_elected:

            # eliminate the candidate with the least votes
            min_votes = min(tally.values())
            lowest_candidates: list[int] = [c for c, v in tally.items() if v == min_votes]
            to_eliminate = min(lowest_candidates)  # kinda arbitrary tie break but whatever
            eliminated.add(to_eliminate)
            result_message += f"<@{to_eliminate}> eliminated with {min_votes} votes.\n"

            for i, ballot in enumerate(ballots):
                ballots[i] = [c for c in ballot if c != to_eliminate]

        curr_round += 1

    # if there's still unfilled seats, fill them by who got the most votes (even if they didn't meet quota)
    remaining_seats = available_seats - len(elected)
    if remaining_seats > 0:
        remaining_candidates = list(all_candidates - set(elected) - eliminated)

        final_tally: dict[int, int] = collections.defaultdict(float)
        for i, ballot in enumerate(ballots):
            for choice in ballot:
                if choice in remaining_candidates:
                    final_tally[choice] += weights[i]
                    break
        sorted_remaining = sorted(final_tally.items(), key=lambda x: (-x[1], x[0]))
        for c, _ in sorted_remaining[:remaining_seats]:
            elected.append(c)
            result_message += f"Filling remaining seat with <@{c}>\n"

    return result_message, elected
