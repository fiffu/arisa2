-- SQLite

DROP TABLE IF EXISTS messages;
CREATE TABLE "messages" (
    id              INTEGER PRIMARY KEY,
    content         TEXT    NOT NULL,  -- 'raw text'
    authorid        INTEGER NOT NULL,
    channelid       INTEGER NOT NULL,
    channeltype     TEXT
);


DROP TABLE IF EXISTS emojiuse;
CREATE TABLE "emojiuse" (
    messageid  INTEGER  PRIMARY KEY,
    emojiname  TEXT     NOT NULL,
    customid   INTEGER,            -- blank if it's Unicode emoji
    count      INTEGER  DEFAULT 1,
    reacterid  INTEGER,            -- sender's userid if this is a react
    FOREIGN KEY (messageid)
        REFERENCES messages (id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

DROP TABLE IF EXISTS users;
CREATE TABLE "users" (
    userid      INTEGER NOT NULL,
    guildid     INTEGER,
    username    TEXT,
    displayname TEXT,
    PRIMARY KEY (userid, guildid)
)
