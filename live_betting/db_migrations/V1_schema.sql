DROP TABLE IF EXISTS match_course;
DROP TABLE IF EXISTS bet;
DROP TABLE IF EXISTS inplay;
DROP TABLE IF EXISTS odds;
DROP TABLE IF EXISTS matches_bookmaker;
DROP TABLE IF EXISTS matches;
DROP TABLE IF EXISTS tournament_bookmaker;
DROP TABLE IF EXISTS tournament;
DROP TABLE IF EXISTS bookmaker;

DROP TYPE IF EXISTS TOURNAMENT_TYPE;
DROP TYPE IF EXISTS SEX;
DROP TYPE IF EXISTS SURFACE;
DROP TYPE IF EXISTS ODDSTYPE;
DROP TYPE IF EXISTS MATCHPART;
DROP TYPE IF EXISTS BETTYPE;

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

CREATE TYPE ODDSTYPE AS ENUM (
    'home_away',
    'over_under',
    'handicap',
    'correct_score'
    );

CREATE TYPE MATCHPART AS ENUM (
    'match',
    'set1',
    'set2',
    'set3',
    'set4',
    'set5'
    );

CREATE TYPE BETTYPE AS ENUM (
    'home',
    'away'
    );

CREATE TABLE bookmaker (
    id       BIGSERIAL NOT NULL PRIMARY KEY,
    name     VARCHAR   NOT NULL UNIQUE,
    home_url VARCHAR   NOT NULL UNIQUE
);

INSERT INTO bookmaker (name, home_url)
VALUES ('Tipsport', 'https://www.tipsport.cz');



CREATE TABLE tournament (
    id      BIGSERIAL       NOT NULL PRIMARY KEY,
    name    VARCHAR         NOT NULL,
    sex     SEX             NOT NULL,
    type    TOURNAMENT_TYPE NOT NULL,
    surface SURFACE         NOT NULL,
    "year"  INTEGER         NOT NULL,
    UNIQUE (name, sex, type, year)
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
    id             BIGSERIAL   NOT NULL PRIMARY KEY,
    home           VARCHAR     NOT NULL,
    away           VARCHAR     NOT NULL,
    start_time_utc TIMESTAMPTZ NOT NULL,
    tournament_id  BIGINT      NOT NULL REFERENCES tournament(id) ON DELETE CASCADE ON UPDATE CASCADE,
    UNIQUE (home, away, tournament_id)
);

CREATE TABLE matches_bookmaker (
    id                 BIGSERIAL NOT NULL PRIMARY KEY,
    match_id           BIGINT    NOT NULL REFERENCES matches(id) ON DELETE CASCADE ON UPDATE CASCADE,
    bookmaker_id       BIGINT    NOT NULL REFERENCES bookmaker(id) ON DELETE CASCADE ON UPDATE CASCADE,
    match_bookmaker_id VARCHAR,
    UNIQUE (match_id, bookmaker_id),
    UNIQUE (bookmaker_id, match_bookmaker_id)
);

CREATE TABLE odds (
    id                 BIGSERIAL   NOT NULL PRIMARY KEY,
    bookmaker_id       BIGINT      NOT NULL,
    match_bookmaker_id VARCHAR     NOT NULL,
    odds_type          ODDSTYPE    NOT NULL,
    match_part         MATCHPART   NOT NULL,
    odd1               FLOAT       NOT NULL,
    odd2               FLOAT       NOT NULL,
    utc_time_recorded  TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (bookmaker_id, match_bookmaker_id) REFERENCES matches_bookmaker(bookmaker_id, match_bookmaker_id) ON DELETE CASCADE ON UPDATE CASCADE,
    UNIQUE (bookmaker_id, match_bookmaker_id, odds_type, match_part)
);

CREATE TABLE inplay (
    id                 BIGSERIAL   NOT NULL PRIMARY KEY,
    bookmaker_id       BIGINT      NOT NULL,
    match_bookmaker_id VARCHAR     NOT NULL,
    utc_time_recorded  TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (bookmaker_id, match_bookmaker_id) REFERENCES matches_bookmaker(bookmaker_id, match_bookmaker_id) ON DELETE CASCADE ON UPDATE CASCADE,
    UNIQUE (bookmaker_id, match_bookmaker_id)
);

CREATE TABLE bet (
    id                 BIGSERIAL   NOT NULL PRIMARY KEY,
    bookmaker_id       BIGINT      NOT NULL,
    match_bookmaker_id VARCHAR     NOT NULL,
    bet_type           BETTYPE     NOT NULL,
    match_part         MATCHPART   NOT NULL,
    odd                FLOAT       NOT NULL,
    probability        FLOAT       NOT NULL,
    result             BOOLEAN,
    utc_time_recorded  TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (bookmaker_id, match_bookmaker_id) REFERENCES matches_bookmaker(bookmaker_id, match_bookmaker_id) ON DELETE CASCADE ON UPDATE CASCADE,
    UNIQUE (bookmaker_id, match_bookmaker_id, bet_type, match_part)
);

CREATE TABLE match_course (
    id                BIGSERIAL   NOT NULL PRIMARY KEY,
    match_id          BIGINT      NOT NULL,
    set_number        INT         NOT NULL,
    result            BETTYPE     NOT NULL,
    utc_time_recorded TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE ON UPDATE CASCADE,
    UNIQUE (match_id, set_number)
);


CREATE TABLE bet_manually_updated (
    id                 BIGSERIAL   NOT NULL PRIMARY KEY,
    bookmaker_id       BIGINT      NOT NULL,
    match_bookmaker_id VARCHAR     NOT NULL,
    bet_type           BETTYPE     NOT NULL,
    match_part         MATCHPART   NOT NULL,
    odd                FLOAT       NOT NULL,
    probability        FLOAT       NOT NULL,
    result             BOOLEAN,
    utc_time_recorded  TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (bookmaker_id, match_bookmaker_id) REFERENCES matches_bookmaker(bookmaker_id, match_bookmaker_id) ON DELETE CASCADE ON UPDATE CASCADE,
    UNIQUE (bookmaker_id, match_bookmaker_id, bet_type, match_part)
);