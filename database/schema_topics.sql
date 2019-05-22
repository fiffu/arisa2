DROP TABLE IF EXISTS topics_channels;
CREATE TABLE "topics_channels" (
    topic       TEXT    NOT NULL,
    channelid   BIGINT  NOT NULL,
    channelname TEXT,
    guildid     BIGINT,
    guildname   TEXT,
    isactive    BOOLEAN NOT NULL,
    PRIMARY KEY (channelid, topic)
);
