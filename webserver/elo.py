import math
from enum import Enum
from typing import List

import numpy as np


def expected_result(loc, aw):
    dr = loc - aw
    we = (1 / (10 ** (-dr / 400) + 1))
    return [np.round(we, 3), 1 - np.round(we, 3)]


def actual_result(team1_score, team2_score):
    if team1_score < team2_score:
        wa = 1
        wl = 0
    elif team1_score > team2_score:
        wa = 0
        wl = 1
    else:  # team1_score == team2_score
        wa = 0.5
        wl = 0.5
    return [wl, wa]


def calculate_elo(team1_elo, team2_elo, team1_score, team2_score):
    k = 60  # TODO: balance
    if team1_score > team2_score:
        ELOW = team1_elo
        ELOL = team2_elo
    else:
        ELOW = team2_elo
        ELOL = team1_elo

    k = k * (math.log(abs(team1_score - team2_score) + 1, 2) * (2.2 / ((ELOW - ELOL) * .001 + 2.2)))
    wl, wv = actual_result(team1_score, team2_score)
    wel, wev = expected_result(team1_elo, team2_elo)

    elo_ln = team1_elo + k * (wl - wel)
    elo_vn = team2_elo + k * (wv - wev)

    return int(elo_ln), int(elo_vn)


csgo_rank_dist = [1.6, 2.9, 2.7, 3.6, 4.9, 6.0, 7.2, 8.2, 8.9, 9.4, 9.0, 8.3, 7.2, 6.1, 4.8, 4.9, 3.1, 1.3]
csgo_elo_dist = [1000 + (600 * sum(csgo_rank_dist[:i + 1])) / 100 for i in range(0, len(csgo_rank_dist))]
print(csgo_elo_dist)


class CSRank(Enum):
    Silver_1 = 0
    Silver_2 = 1
    Silver_3 = 2
    Silver_4 = 3
    Silver_Elite = 4
    Silver_Elite_Master = 5
    Gold_Nova_1 = 6
    Gold_Nova_2 = 7
    Gold_Nova_3 = 8
    Gold_Nova_Master = 9
    Master_Guardian_1 = 10
    Master_Guardian_2 = 11
    Master_Guardian_Elite = 12
    Distinguished_Master_Guardian = 13
    Legendary_Eagle = 14
    Legendary_Eagle_Master = 15
    Supreme_Master_First_Class = 16
    Global_Elite = 17


def calculate_team_elo(team_ranks: List[CSRank]):
    return sum([csgo_elo_dist[rank.value] for rank in team_ranks]) / len(team_ranks)


def main():
    # print(calculate_team_elo([CSRank(int(input("?: "))) for _ in range(5)]))

    team1 = calculate_team_elo([
        CSRank.Supreme_Master_First_Class,
        CSRank.Supreme_Master_First_Class,
        CSRank.Supreme_Master_First_Class,
        CSRank.Supreme_Master_First_Class,
        CSRank.Supreme_Master_First_Class
    ])

    team2 = calculate_team_elo([
        CSRank.Distinguished_Master_Guardian,
        CSRank.Master_Guardian_2,
        CSRank.Master_Guardian_2,
        CSRank.Master_Guardian_Elite,
        CSRank.Legendary_Eagle
    ])

    print(f"Team1 elo is: {team1}")
    print(f"Team2 elo is: {team2}")

    print(expected_result(1200, 1250))
    for i in range(0, 17):
        for j in range(0, 17):
            if i != 16 and j != 16:
                continue

            scores = [int(x) for x in calculate_elo(team1, team2, i, j)]
            print(
                f"{i}:{j}, {int(team1)} vs {int(team2)} -> {scores[0]} and {scores[1]}, change: {int(scores[0] - team1)} and {int(scores[1] - team2)}")


if __name__ == '__main__':
    main()
