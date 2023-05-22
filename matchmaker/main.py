import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

import time
from utils import elo, db_models

ALREADY_PLAYED_PUNISHER = 200


def main():
    while True:
        logging.info("Starting matchmaker loop, sleeping for 10 seconds")
        time.sleep(10)

        competing_teams = db_models.Team.select().where(db_models.Team.competing <= 1)
        logging.info(f"Found {len(competing_teams)} competing teams for consideration")

        ongoing_matches = db_models.Match.select().where(db_models.Match.finished < 1)
        logging.info(f"Found {len(ongoing_matches)} ongoing matches")

        # sort out competing teams that are already in a match
        competing_teams = [team for team in competing_teams if not any(
            [team.id == match.team1.id or team.id == match.team2.id for match in ongoing_matches])]
        logging.info(f"Found {len(competing_teams)} competing teams that are not in a match")

        if len(competing_teams) < 2:
            logging.info("Not enough competing teams to start a match")
            continue

        logging.info("Extracting elo of teams...")
        team_elo_ratings = {team.id: team.elo for team in competing_teams}
        logging.info(f"Team elo ratings: {team_elo_ratings}")

        logging.info("Creating matched matrix...")
        played_matches_matrix = {team.id: {team.id: 0 for team in competing_teams} for team in competing_teams}

        finished_matches = db_models.Match.select().where(db_models.Match.finished == 3)
        for match in finished_matches:
            played_matches_matrix[match.team1.id][match.team2.id] += ALREADY_PLAYED_PUNISHER
            played_matches_matrix[match.team2.id][match.team1.id] += ALREADY_PLAYED_PUNISHER

        logging.info(f"Played matches matrix: {played_matches_matrix}")


if __name__ == '__main__':
    main()
