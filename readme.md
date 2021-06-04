# CSGO Tournament Manager

## Status

**The software is currently in development** for the airlan21 (25.06.2021). A small csgo tournament organized for
team-building by robo4you.at.

## What does this software do?

It manages a number of get5 servers for small to medium lan parties. E.g. the webinterface lets you define new matches
by selecting players and creating teams. You can then select a free server, and the match config file will be
transferred and loaded to the csgo server. It also displays some basic statistics about the servers.

It is recommended to install a [csgosl](https://github.com/lenosisnickerboa/csgosl) server on a virtual machine.
(in our setup we use proxmox and clone our "template" machine with csgo installed until we have enough servers running).
We also thought about using our kubernetes cluster and creating csgo servers on demand but that would be overkill for a
small project like this.

This software is completely standalone and is **NOT** part of your csgo server installation. It simply communicates with
your servers using the rcon protocol.

## How to use this software?

Edit the `app/config.json` and include all your servers. It is currently not supported to add servers during runtime.
Also all the servers have to be running because the software establishes a rcon connection to each of them at the
beginning.

Then start the server like: `docker-compose up --build`
