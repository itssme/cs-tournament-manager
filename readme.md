# CSGO Tournament Manager

## Status

The software has been in developed for the airlan21 (25.06.2021). A small csgo tournament organized for
team-building by robo4you.at.

**Currently, it is being updated and rewritten** for the 'airlan Winter Edition' which will take place in early january

2023.

## What does this software do?

It manages a number of get5 servers for small to medium lan parties. E.g. the webinterface lets you define new matches
by selecting players and creating teams. You can then select a free server, and the match config file will be
transferred and loaded to the csgo server. It also displays some basic statistics about the servers.

## How to use this software?

+ Edit the `teams.json` file to include all your teams and players. This file will be mounted in the dockerfile.
+ Then start the server like: `docker-compose up --build`
+ Goto `http://127.0.0.1` and add created matches.
+ The match will be started in a docker container and be visible in the `/status` page.

## Banned Players

| SteamID              | Reason                              |
|----------------------|-------------------------------------|
| STEAM_0:1:148684053  | Cheating during airlan21 (wallhack) |
| STEAM_0:1:159656029  | Cheating during airlan21 (wallhack) |
