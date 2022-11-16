create table if not exists players
(
    id       serial primary key,
    name     text        not null,
    steam_id text unique not null
);

create table if not exists teams
(
    id   serial primary key,
    tag  text        not null,
    name text unique not null
);

create table if not exists team_assignments
(
    team   integer references teams,
    player integer references players,
    primary key (team, player)
);

create table if not exists servers
(
    id         serial primary key,
    name       text not null,
    status     int                         default 0,
    port       int                         default -1,
    team1      integer references teams default null,
    team2      integer references teams default null,
    gslt_token text default null
);
