DROP TABLE IF EXISTS topics CASCADE;
CREATE TABLE "topics" (
    name TEXT PRIMARY KEY
);


DROP TABLE IF EXISTS topics_channels;
CREATE TABLE "topics_channels" (
    channelid   BIGINT  NOT NULL,
    channelname TEXT    NOT NULL,
    guildname   TEXT,
    active      BOOLEAN NOT NULL,
    topic       TEXT    NOT NULL REFERENCES topics(name) ON DELETE CASCADE,
    PRIMARY KEY (channelid, topic)
);
