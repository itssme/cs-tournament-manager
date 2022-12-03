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
    k = 200  # TODO: balance
    wl, wv = actual_result(team1_score, team2_score)
    wel, wev = expected_result(team1_elo, team2_elo)

    elo_ln = team1_elo + k * (wl - wel)
    elo_vn = team2_elo + k * (wv - wev)

    return elo_ln, elo_vn


def main():
    teams = [1000, 2000, 1500, 800]

    print(calculate_elo(1200, 2000, 16, 20))


if __name__ == '__main__':
    main()
