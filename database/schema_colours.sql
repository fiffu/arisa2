DROP TABLE IF EXISTS colours;
CREATE TABLE "colours" (
    userid          BIGINT      NOT NULL,
    mutateorreroll  TEXT        NOT NULL,
    tstamp          TIMESTAMP   NOT NULL,
    colour          TEXT,
    is_frozen       BOOLEAN,
    PRIMARY KEY (userid, mutateorreroll)
);
