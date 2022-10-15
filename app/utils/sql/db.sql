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
