import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

import os
import time
import requests

from utils.utils_funcs import get_api_login_token
from typing import List
from utils import elo, db_models

MANAGER_IP = os.getenv("MANAGER_IP", "cs2_manager")
logging.info(f"Manager IP: {MANAGER_IP}")


def start_match(team1: db_models.Team, team2: db_models.Team) -> bool:
    match = {
        "team1": team1.id,
        "team2": team2.id,
        "best_of": 1,
        "check_auths": True
    }

    logging.info(f"Starting match: {match}")

    res = requests.post(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{MANAGER_IP}/api/match",
                        json=match,
                        cookies={"access_token": get_api_login_token()})

    if res.status_code == 200:
        logging.info(f"Successfully started match: {match}")
        return True
    else:
        logging.error(f"Failed to start match: {match}")
        return False


def main():
    while True:
        competing_teams = db_models.Team.select().where(db_models.Team.competing <= 1)
        logging.info(
            f"Found {len(competing_teams)} competing teams for consideration ({', '.join([str(team.name) for team in competing_teams])})")

        ongoing_matches = db_models.Match.select().where(db_models.Match.finished < 1)
        logging.info(
            f"Found {len(ongoing_matches)} ongoing matches ({', '.join([str(match.matchid) for match in ongoing_matches])})")

        # sort out competing teams that are already in a match
        competing_teams: List[db_models.Team] = [team for team in competing_teams if not any(
            [team.id == match.team1.id or team.id == match.team2.id for match in ongoing_matches])]
        logging.info(
            f"Found {len(competing_teams)} competing teams that are not in a match ({', '.join([str(team.name) for team in competing_teams])})")

        if len(competing_teams) < 2:
            logging.info("Not enough competing teams to start a match")
            continue

        logging.info("Starting new round of matchmaking")
        elo_already_played_punisher = int(
            db_models.Config.get(db_models.Config.key == "elo_already_played_punisher").value)
        k_factor = int(db_models.Config.get(db_models.Config.key == "elo_k_factor").value)

        logging.info("Loaded config")
        logging.info(f"elo_already_played_punisher: {elo_already_played_punisher}")
        logging.info(f"k_factor: {k_factor}")

        logging.info("Extracting elo of teams...")
        team_elo_ratings = {team.id: team.elo for team in competing_teams}
        logging.info(f"Team elo ratings: {team_elo_ratings}")

        logging.info("Creating matched matrix...")
        played_matches_matrix = {team.id: {team.id: 0 for team in competing_teams} for team in competing_teams}

        finished_matches = db_models.Match.select().where(db_models.Match.finished == 3)
        for match in finished_matches:
            played_matches_matrix[match.team1.id][match.team2.id] += 1
            played_matches_matrix[match.team2.id][match.team1.id] += 1

        logging.info(f"Played matches matrix: {played_matches_matrix}")

        logging.info("Creating possible matches...")
        possible_matches = []
        for team1 in competing_teams:
            for team2 in competing_teams:
                if team1.id == team2.id:
                    continue

                possible_matches.append((team1, team2, abs(team1.elo - team2.elo) + played_matches_matrix[team1.id][
                    team2.id] * elo_already_played_punisher))

        logging.info(f"Found {len(possible_matches)} possible matches: {possible_matches}")

        logging.info("Sorting possible matches...")
        possible_matches.sort(key=lambda x: x[2])
        logging.info(f"Sorted possible matches: {possible_matches}")

        logging.info("Starting best matches...")
        occupied_teams = []
        started_matches = []
        while len(possible_matches) > 0:
            team1, team2, elo_diff = possible_matches.pop(0)
            if team1.id in occupied_teams or team2.id in occupied_teams:
                continue

            logging.info("----------------------------------------")
            logging.info(f"Starting match between '{team1.name}' and '{team2.name}'")
            logging.info("----------------------------------------")
            if start_match(team1, team2):
                occupied_teams.append(team1.id)
                occupied_teams.append(team2.id)

                started_matches.append((team1, team2, elo_diff))

        logging.info(f"Started {len(started_matches)} matches: {started_matches}")
        for team1, team2, elo_diff in started_matches:
            logging.info(
                f"Started: '{team1.name}' ELO=({team1.elo}) - '{team2.name}' ELO=({team2.elo}), ELO_DIFF=({elo_diff})")

        logging.info("Finished matchmaker loop, sleeping for 10 seconds")
        time.sleep(10)


if __name__ == '__main__':
    main()
