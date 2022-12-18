create table if not exists player
(
    id       serial primary key,
    name     text        not null,
    steam_id text unique not null
);

create table if not exists team
(
    id   serial primary key,
    tag  text        not null,
    name text unique not null,
    elo  int default 0
);

create table if not exists team_assignment
(
    team   integer references team on delete cascade,
    player integer references player on delete cascade,
    primary key (team, player)
);


create table if not exists match
(
    id                   serial primary key,
    matchid              text    not null unique,
    name                 text    not null,
    team1                integer references team default null,
    team2                integer references team default null,
    best_out_of          integer not null,
    number_in_map_series integer                 default 0,
    series_score_team1   integer                 default 0,
    series_score_team2   integer                 default 0,
    finished             integer                 default -1 -- -1 game is not ready, 0 game is running, 1 game is finished, 2 game is finished and demo is uploaded, 3 failed/ stopped
);

create table if not exists server
(
    id             serial primary key,
    status         int  default 0,
    port           int  default -1,
    gslt_token     text default null,
    container_name text default null,
    match          integer references match
);
