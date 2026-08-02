PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE workspaces (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    name_key VARCHAR NOT NULL,
    created_at DATETIME NOT NULL
);
INSERT INTO workspaces VALUES('ws_legacy','Legado','legado','2026-08-02T00:00:00');
CREATE TABLE projects (
    id VARCHAR PRIMARY KEY,
    workspace_id VARCHAR NOT NULL REFERENCES workspaces(id),
    name VARCHAR NOT NULL,
    name_key VARCHAR NOT NULL,
    created_at DATETIME NOT NULL
);
INSERT INTO projects VALUES('prj_legacy','ws_legacy','Projeto','projeto','2026-08-02T00:00:00');
CREATE TABLE chat_sessions (
    id VARCHAR PRIMARY KEY,
    workspace_id VARCHAR NOT NULL REFERENCES workspaces(id),
    scope_type VARCHAR,
    scope_id VARCHAR,
    title VARCHAR NOT NULL,
    created_at DATETIME NOT NULL
);
INSERT INTO chat_sessions VALUES(
    'chat_legacy',
    'ws_legacy',
    'project',
    'prj_legacy',
    'Título cita prj_legacy mas não concede escopo',
    '2026-08-02T00:00:00'
);
CREATE TABLE chat_messages (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR NOT NULL REFERENCES chat_sessions(id),
    role VARCHAR NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL
);
INSERT INTO chat_messages VALUES(
    'msg_b',
    'chat_legacy',
    'custom_role',
    'Conteúdo cita prj_legacy e deve ser preservado',
    '2026-08-02T01:00:00'
);
INSERT INTO chat_messages VALUES(
    'msg_a','chat_legacy','human','Primeiro','2026-08-02T01:00:00'
);
INSERT INTO chat_messages VALUES(
    'msg_c','chat_legacy','agent','Terceiro','2026-08-02T02:00:00'
);
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);
INSERT INTO alembic_version VALUES('0007_execution_trust_foundation');
COMMIT;
