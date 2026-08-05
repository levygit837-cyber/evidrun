PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE workspaces (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    name_key VARCHAR NOT NULL,
    created_at DATETIME NOT NULL
);
INSERT INTO workspaces VALUES('ws_v0008','Workspace anterior','workspace anterior','2026-08-02T00:00:00');
CREATE TABLE chat_sessions (
    id VARCHAR PRIMARY KEY,
    workspace_id VARCHAR NOT NULL REFERENCES workspaces(id),
    project_id VARCHAR,
    focus_kind VARCHAR,
    focus_id VARCHAR,
    scope_type VARCHAR,
    scope_id VARCHAR,
    title VARCHAR NOT NULL,
    created_at DATETIME NOT NULL
);
INSERT INTO chat_sessions VALUES(
    'chat_v0008','ws_v0008',NULL,NULL,NULL,NULL,NULL,'Sessão anterior','2026-08-02T00:00:00'
);
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);
INSERT INTO alembic_version VALUES('0008_lab_agent_session_store');
COMMIT;
