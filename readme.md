# CSGO Tournament Manager

## Status

The software has been developed for the airlan21 (25.06.2021). A small csgo tournament organized for
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

### Telegram BOT

+ Create .env file in the folder `telegram_bot/.env`
+ Fill it with the following content:

```env
BOT_TOKEN=your_token_here
CHAT_IDS="chat_id_1,chat_id_2..."
```

+ The first line is the telegram bot token of you bot. The second line specifies who has access to the bot and can send
  it messages/ commands. If you are not sure what your chat_id is, then leave the field empty for the time being and run
  the bot only with the bot token. Then add your bot and type `/help` in the chat. Look at the log files of the
  software, and you will se your chat_id printed there.

## Banned Players

| SteamID              | Reason                              |
|----------------------|-------------------------------------|
| STEAM_0:1:148684053  | Cheating during airlan21 (wallhack) |
| STEAM_0:1:159656029  | Cheating during airlan21 (wallhack) |
