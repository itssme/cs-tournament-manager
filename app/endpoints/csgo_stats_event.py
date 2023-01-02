import logging
from enum import Enum
from typing import Dict

from sql import db


class Events(Enum):
    round_mvp = 0
    grenade_thrown = 1
    player_death = 2
    hegrenade_detonated = 3
    molotov_detonated = 4
    flashbang_detonated = 5
    smokegrenade_detonated = 6
    decoygrenade_started = 7
    bomb_planted = 8
    bomb_defused = 9
    bomb_exploded = 10
    player_kills = 11  # event derived from player_death, this event says a plyer has killed someone else


event_map = {
    "round_mvp": Events.round_mvp,
    "grenade_thrown": Events.grenade_thrown,
    "player_death": Events.player_death,
    "hegrenade_detonated": Events.hegrenade_detonated,
    "molotov_detonated": Events.molotov_detonated,
    "flashbang_detonated": Events.flashbang_detonated,
    "smokegrenade_detonated": Events.smokegrenade_detonated,
    "decoygrenade_started": Events.decoygrenade_started,
    "bomb_planted": Events.bomb_planted,
    "bomb_defused": Events.bomb_defused,
    "bomb_exploded": Events.bomb_exploded,
    "player_kills": Events.player_kills
}

steamid64ident = 76561197960265728


def commid_to_steamid(commid):
    steamid = ['STEAM_0:']
    steamidacct = int(commid) - steamid64ident

    if steamidacct % 2 == 0:
        steamid.append('0:')
    else:
        steamid.append('1:')

    steamid.append(str(steamidacct // 2))

    return ''.join(steamid)


def stats_event(event: Dict):
    event_type = event_map[event["event"]]

    match = db.get_match_by_matchid(event["matchid"])
    if event_type != Events.bomb_exploded:
        player = db.get_player_by_steam_id(commid_to_steamid(event["player"]["steamid"]))
        stats = db.Stats(None, match.id, player.id, event_type.value)

        if event_type == Events.player_death:
            player = db.get_player_by_steam_id(commid_to_steamid(event["attacker"]["steamid"]))
            stats = db.Stats(None, match.id, player.id, Events.player_kills.value)
    else:
        stats = db.Stats(None, match.id, None, event_type.value)

    stats.insert_into_db()
    # logging.info(f"Event: {event_type} -> {stats}")
