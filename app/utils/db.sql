create table if not exists players
(
    name     text primary key,
    steam_id text unique
);

create table if not exists teams
(
    teamname text primary key
);

create table if not exists team_assignments
(
    team   text references teams,
    player text references players,
    primary key (team, player)
);
