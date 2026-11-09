"""Additive agent tables in the existing production ledger; no media or third DB."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS director_goals (
    project_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    objective TEXT NOT NULL,
    status TEXT NOT NULL,
    thread_id TEXT,
    state_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, request_id)
);
CREATE TABLE IF NOT EXISTS director_goal_steps (
    project_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    step_key TEXT NOT NULL,
    tool TEXT NOT NULL,
    arguments_json TEXT NOT NULL,
    task_id TEXT,
    status TEXT NOT NULL,
    result_json TEXT,
    PRIMARY KEY (project_id, request_id, step_key),
    FOREIGN KEY (project_id, request_id) REFERENCES director_goals(project_id, request_id)
);
CREATE TABLE IF NOT EXISTS agent_knowledge (
    project_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, revision)
);
CREATE TABLE IF NOT EXISTS agent_messages (
    project_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    text TEXT NOT NULL,
    reply TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    task_id TEXT,
    context_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, request_id)
);
CREATE TABLE IF NOT EXISTS agent_tasks (
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    status TEXT NOT NULL,
    current_revision INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, task_id)
);
CREATE TABLE IF NOT EXISTS agent_task_plans (
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    plan_hash TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    PRIMARY KEY (project_id, task_id, revision),
    UNIQUE (project_id, task_id, revision, plan_hash),
    FOREIGN KEY (project_id, task_id) REFERENCES agent_tasks(project_id, task_id)
);
CREATE TABLE IF NOT EXISTS agent_task_approvals (
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    plan_hash TEXT NOT NULL,
    approved_at TEXT NOT NULL,
    PRIMARY KEY (project_id, task_id, revision, plan_hash),
    FOREIGN KEY (project_id, task_id, revision, plan_hash)
        REFERENCES agent_task_plans(project_id, task_id, revision, plan_hash)
);
CREATE TABLE IF NOT EXISTS agent_invocations (
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    plan_hash TEXT NOT NULL,
    invocation_id TEXT NOT NULL UNIQUE,
    job_id TEXT UNIQUE,
    state TEXT NOT NULL,
    PRIMARY KEY (project_id, task_id, revision),
    FOREIGN KEY (project_id, task_id, revision, plan_hash)
        REFERENCES agent_task_approvals(project_id, task_id, revision, plan_hash)
);
CREATE TABLE IF NOT EXISTS agent_task_events (
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, task_id, sequence),
    FOREIGN KEY (project_id, task_id) REFERENCES agent_tasks(project_id, task_id)
);
"""
