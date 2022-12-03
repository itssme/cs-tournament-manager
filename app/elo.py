import numpy as np


def expected_result(loc, aw):
    dr = loc - aw
    we = (1 / (10 ** (-dr / 400) + 1))
    return [np.round(we, 3), 1 - np.round(we, 3)]


def actual_result(loc, aw):
    if loc < aw:
        wa = 1
        wl = 0
    elif loc > aw:
        wa = 0
        wl = 1
    elif loc == aw:
        wa = 0.5
        wl = 0.5
    return [wl, wa]


def calculate_elo(elo_l, elo_v, local_goals, away_goals):
    k = 10  # TODO: balance
    wl, wv = actual_result(local_goals, away_goals)
    wel, wev = expected_result(elo_l, elo_v)

    elo_ln = elo_l + k * (wl - wel)
    elo_vn = elo_v + k * (wv - wev)

    return elo_ln, elo_vn
