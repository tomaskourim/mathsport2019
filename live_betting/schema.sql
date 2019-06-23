DROP TABLE IF EXISTS matches_bookmaker;
DROP TABLE IF EXISTS matches;
DROP TABLE IF EXISTS tournament_bookmaker;
DROP TABLE IF EXISTS tournament;
DROP TABLE IF EXISTS bookmaker;

DROP TYPE IF EXISTS TOURNAMENT_TYPE;
DROP TYPE IF EXISTS SEX;
DROP TYPE IF EXISTS SURFACE;

CREATE TABLE bookmaker (
    id       BIGSERIAL NOT NULL PRIMARY KEY,
    name     VARCHAR   NOT NULL UNIQUE,
    home_url VARCHAR   NOT NULL UNIQUE
);

INSERT INTO bookmaker (name, home_url)
VALUES ('Tipsport', 'https://www.tipsport.cz');

CREATE TYPE TOURNAMENT_TYPE AS ENUM (
    'singles',
    'doubles',
    'teams'
    );

CREATE TYPE SEX AS ENUM (
    'men',
    'women'
    );

CREATE TYPE SURFACE AS ENUM (
    'clay',
    'grass',
    'hard'
    );

CREATE TABLE tournament (
    id      BIGSERIAL       NOT NULL PRIMARY KEY,
    name    VARCHAR         NOT NULL,
    sex     SEX             NOT NULL,
    type    TOURNAMENT_TYPE NOT NULL,
    surface SURFACE         NOT NULL,
    "year"  INTEGER         NOT NULL,
    UNIQUE (name, sex, year)
);

CREATE TABLE tournament_bookmaker (
    id                            BIGSERIAL NOT NULL PRIMARY KEY,
    tournament_id                 BIGINT    NOT NULL REFERENCES tournament(id) ON DELETE CASCADE ON UPDATE CASCADE,
    bookmaker_id                  BIGINT    NOT NULL REFERENCES bookmaker(id) ON DELETE CASCADE ON UPDATE CASCADE,
    tournament_bookmaker_id       VARCHAR,
    tournament_bookmaker_extra_id VARCHAR,
    UNIQUE (tournament_id, bookmaker_id)
);

CREATE TABLE matches (
    id            BIGSERIAL NOT NULL PRIMARY KEY,
    home          VARCHAR   NOT NULL,
    away          VARCHAR   NOT NULL,
    start_date    DATE      NOT NULL,
    start_time    TIME      NOT NULL,
    tournament_id BIGINT    NOT NULL REFERENCES tournament(id) ON DELETE CASCADE ON UPDATE CASCADE,
    UNIQUE (home, away, tournament_id)
);

CREATE TABLE matches_bookmaker (
    id                 BIGSERIAL NOT NULL PRIMARY KEY,
    match_id           BIGINT    NOT NULL REFERENCES matches(id) ON DELETE CASCADE ON UPDATE CASCADE,
    bookmaker_id       BIGINT    NOT NULL REFERENCES bookmaker(id) ON DELETE CASCADE ON UPDATE CASCADE,
    match_bookmaker_id VARCHAR,
    UNIQUE (match_id, bookmaker_id)
);