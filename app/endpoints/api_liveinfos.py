from fastapi import Depends
from starlette.requests import Request
from starlette.responses import JSONResponse

from endpoints import public_routes, auth_api
from endpoints.csgo_stats_event import event_map
from rcon import get5_status, RCON
from sql import db, db_stats


def set_api_routes(app, cache):
    @app.get("/status", response_class=JSONResponse)
    @cache(namespace="status", expire=4)
    async def status(request: Request):
        matches = []
        teams = []

        matches_db = db.get_matches()
        for match in matches_db:
            if match.finished <= 0:
                score = [0, 0]
                team1 = db.get_team_by_id(match.team1)
                team2 = db.get_team_by_id(match.team2)
                server = db.get_server_for_match(match.matchid)

                try:
                    get5_stats = get5_status(server.ip, server.port)
                    if "team1" in get5_stats.keys() and "team2" in get5_stats.keys():
                        score = [get5_stats["team1"]["current_map_score"], get5_stats["team2"]["current_map_score"]]
                except ConnectionRefusedError as e:
                    get5_stats = {"gamestate": "unreachable"}

                matches.append(
                    {"score": score, "teamnames": [team1.name, team2.name], "team_elo": [team1.elo, team2.elo],
                     "server_ip": f"{server.ip}:{server.port}",
                     "status": get5_stats["gamestate"]})

        for team in db.get_teams():
            if team.competing != 2:
                wins = 0
                losses = 0
                draws = 0  # currently not used

                for match in matches_db:
                    if 1 <= match.finished <= 2:
                        if match.team1 == team.id:
                            wins += match.series_score_team1
                            losses += match.series_score_team2
                        elif match.team2 == team.id:
                            wins += match.series_score_team2
                            losses += match.series_score_team1

                teams.append({"teamname": team.name, "elo": team.elo, "wins": wins, "losses": losses, "draws": draws})

        # sort teams by elo
        teams.sort(key=lambda x: x["elo"], reverse=True)

        return {"matches": matches, "teams": teams}

        # for testing
        # return {"matches": [
        #     {"score": [5, 14], "teamnames": ["airplebs", "Faceit LVL 1"],
        #      "server_ip": "10.20.0.20:27015", "team_elo": [1406, 1326], "status": "running"},
        #     {"score": [4, 8], "teamnames": ["Unranked", "Die Globale Elite"],
        #      "server_ip": "10.20.0.20:27027", "team_elo": [1203, 1260], "status": "running"}
        # ], "teams": [{"teamname": "airplebs", "elo": 1406, "wins": 5, "losses": 2, "draws": 0},
        #              {"teamname": "Faceit LVL 1", "elo": 1326, "wins": 3, "losses": 4, "draws": 0},
        #              {"teamname": "Die Globale Elite", "elo": 1260, "wins": 4, "losses": 3, "draws": 0},
        #              {"teamname": "Unranked", "elo": 1203, "wins": 2, "losses": 5, "draws": 0}
        #              ]}

    @app.get("/stats", response_class=JSONResponse)
    @cache(namespace="stats", expire=1)
    async def stats(request: Request):
        stats = {"version": public_routes.version}

        for event in event_map.keys():
            stats[event] = {}
            stats[event]["occurred"] = db_stats.count_event_type(event_map[event])
            stats[event]["players"] = db_stats.player_with_most(event_map[event])

        return stats

    @app.get("/info", response_class=JSONResponse)
    @cache(namespace="info", expire=1)
    async def status(request: Request, current_user: auth_api.User = Depends(auth_api.get_current_user)):
        servers = db.get_servers()

        for server in servers:
            server.gslt_token = None  # avoid leaking gslt tokens

        status_json = []

        for server in servers:
            get5_stats = None
            stats = None
            try:
                get5_stats = get5_status(server.ip, server.port)
                with RCON(server.ip, server.port) as rconn:
                    # logging.info(rconn.exec_command("sm_slay Jöl"))
                    # logging.info(rconn.exec_command("cvarlist"))

                    # need to parse values: CPU   NetIn   NetOut    Uptime  Maps   FPS   Players  Svms    +-ms   ~tick
                    stats = rconn.exec_command("stats")
            except ConnectionRefusedError as e:
                pass

            stats_parsed = [float(value) for value in stats.split("\\n")[1].split(" ") if
                            value != ''] if stats is not None else []

            match = db.get_match_by_id(server.match)
            team_1 = db.get_team_by_id(match.team1)
            team_2 = db.get_team_by_id(match.team2)

            if get5_stats is None:
                get5_stats = {"gamestate": "unreachable"}

            get5_stats["matchid"] = f"{team_1.name} vs {team_2.name}"

            status_json.append({"id": server.id,
                                "ip": server.ip + ":" + str(server.port),
                                "get5_stats": get5_stats,
                                "stats": stats_parsed,
                                "team1": team_1,
                                "team2": team_2})

        return status_json
