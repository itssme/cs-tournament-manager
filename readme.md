# CSGO Tournament Manager

## Status

The software has been developed for the airlan21 (25.06.2021). A small csgo tournament organized for
team-building by robo4you.at.

**Currently, it is being updated and rewritten** for the 'airlan Winter Edition' which will take place in early january 2023.

## What does this software do?

It manages a number of get5 servers for small to medium lan parties. E.g. the webinterface (and the telegram bot) lets
you define new matches
by selecting players and creating teams. A new get5 server will then be started in a docker container and the match
config file will be transferred and loaded to the csgo server. It also displays some basic statistics about the servers.

## How to use this software

### 1. Create csgo docker container

+ Go to the folder `get5_image` and run the `build_image.sh` script.
+ This will download the csgo server and automatically install get5. (this step may take some time)

### 2. Create Teams and GSLT file

+ Edit the `teams.json` file to include all your teams and players. This file will be mounted in the dockerfile.
+ Create a `gslt.json` file and include all your GSLT tokens in a list like: `["TOKEN1", "TOKEN2"]`. If you plan on only
  using the servers in a LAN setting, you can simply create the file an leave the list empty (like: `[]`) and then the
  server manager will start the CSGO servers without a GSLT Token. (More information about GSLT
  Tokens: https://developer.valvesoftware.com/wiki/Counter-Strike:_Global_Offensive_Dedicated_Servers)

### 3. Telegram BOT

+ Create .env file in the folder `telegram_bot/.env`
+ Fill it with the following content:

```env
BOT_TOKEN=your_token_here
CHAT_IDS="chat_id_1,chat_id_2..."
```

+ The first line is the telegram bot token of you bot. The second line specifies who has access to the bot and can send
  messages/ commands to it. If you are not sure what your chat_id is, then leave the field empty for the time being and
  run
  the bot only with the bot token. Then add your bot and type `/help` in the chat. Look at the log output of the
  software, and you will see your chat_id printed there.

### 4. Start the software

+ Then start the server like: `docker-compose up --build`
+ Goto `http://127.0.0.1` and create matches. (TODO)
+ The match will be started in a docker container and be visible in the `/status` page. (TODO)
+ (Currently matches can only be started by directly calling the API)

### 5. Connecting to the server

(Note connecting with `127.0.0.1:port` does not work, you need your PCs local IP (like 192.168.x.x or 10.x.x.x etc.) or that of a VPN network)

+ Connect to the server, on the ip shown in the webinterface/ on telegram (todo)

## Banned Players

| SteamID              | Reason                              |
|----------------------|-------------------------------------|
| STEAM_0:1:148684053  | Cheating during airlan21 (wallhack) |
| STEAM_0:1:159656029  | Cheating during airlan21 (wallhack) |
