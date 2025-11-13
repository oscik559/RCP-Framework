-- ═══════════════════════════════════════════════════════════════════════
-- AGENTIC REASONING SYSTEM - DATABASE SCHEMA
-- ═══════════════════════════════════════════════════════════════════════
--
-- This schema supports a hierarchical workflow structure:
--     Goal → Strategy → Function → Parameters/Outputs
--
-- Database Structure:
-- ==================
--
-- Core Workflow Tables:
-- ---------------------
-- - GoalInSession: Top-level user queries and objectives
-- - StrategyInSession: Reasoning strategies selected for each goal
-- - FunctionInSession: Individual function executions within strategies
-- - FunctionOutputInSession: Results produced by function executions
-- - FunctionParametersInSession: Input parameters for function executions
--
-- Template Libraries:
-- ------------------
-- - StrategyLibrary: Reusable strategy templates and plans
-- - FunctionTemplateLibrary: Available function definitions
-- - FunctionOutputLibrary: Expected outputs for each function template
-- - FunctionParametersLibrary: Required parameters for each function template
--
-- Key Features:
-- ============
-- - Foreign key constraints maintain referential integrity
-- - Performance indexes on frequently queried columns
-- - Supports LangGraph-based agentic workflows
-- - Tracks complete execution history and state
-- - Template-based function and strategy definitions
--
-- ═══════════════════════════════════════════════════════════════════════


-- ─── Core Workflow Tables ─────────────────────────────────────────────

-- Top-level goals/queries from users
CREATE TABLE IF NOT EXISTS GoalInSession(
    GoalID          INTEGER PRIMARY KEY AUTOINCREMENT,
    SessionID       INTEGER,
    GoalName        TEXT,
    GoalTarget      TEXT,
    GoalValidation  TEXT,
    GoalDescription TEXT,
    GoalSuccess     INTEGER  -- Tri-state: NULL=pending, 0=failed, 1=success
);

-- Reasoning strategies selected for each goal
CREATE TABLE IF NOT EXISTS StrategyInSession(
    StrategyID          INTEGER PRIMARY KEY AUTOINCREMENT,
    GoalID              INTEGER,
    StrategyName        TEXT,
    StrategyTarget      TEXT,
    StrategyDescription TEXT,
    PlanSteps           TEXT,
    StrategySuccess     INTEGER,  -- Tri-state: NULL=pending, 0=failed, 1=success
    StrategyValidation  TEXT,
    FOREIGN KEY(GoalID) REFERENCES GoalInSession(GoalID)
);

-- Individual function executions within strategies
CREATE TABLE IF NOT EXISTS FunctionInSession(
    FunctionID      INTEGER PRIMARY KEY AUTOINCREMENT,
    StrategyID      INTEGER,
    StrategyName    TEXT,
    FunctionName    TEXT,
    FunctionSuccess INTEGER,  -- Tri-state: NULL=pending, 0=failed, 1=success
    failedtext      TEXT,
    FOREIGN KEY(StrategyID) REFERENCES StrategyInSession(StrategyID)
);

-- Results/outputs produced by function executions
CREATE TABLE IF NOT EXISTS FunctionOutputInSession(
    FunctionOutputID INTEGER PRIMARY KEY AUTOINCREMENT,
    FunctionID       INTEGER,
    FunctionName     TEXT,
    StrategyName     TEXT,
    OutputName       TEXT,
    OutputValue      TEXT,
    Type             TEXT,
    FOREIGN KEY(FunctionID) REFERENCES FunctionInSession(FunctionID)
);

-- Input parameters for function executions
CREATE TABLE IF NOT EXISTS FunctionParametersInSession(
    FunctionParameterID INTEGER PRIMARY KEY AUTOINCREMENT,
    FunctionID          INTEGER,
    FunctionName        TEXT,
    StrategyName        TEXT,
    ParameterName       TEXT,
    ParameterValue      TEXT,
    Type                TEXT,
    FOREIGN KEY(FunctionID) REFERENCES FunctionInSession(FunctionID)
);


-- ─── Template Libraries ───────────────────────────────────────────────

-- Reusable strategy templates
CREATE TABLE IF NOT EXISTS StrategyLibrary(
    StrategyID          INTEGER PRIMARY KEY AUTOINCREMENT,
    StrategyName        TEXT,
    StrategyTarget      TEXT,
    StrategyDescription TEXT,
    PlanSteps           TEXT
);

-- Available function definitions
CREATE TABLE IF NOT EXISTS FunctionTemplateLibrary(
    FunctionTemplateID  INTEGER PRIMARY KEY AUTOINCREMENT,
    FunctionName        TEXT,
    StrategyType        TEXT,
    FunctionDescription TEXT
);

-- Expected outputs for each function template
CREATE TABLE IF NOT EXISTS FunctionOutputLibrary(
    FunctionOutputID   INTEGER PRIMARY KEY AUTOINCREMENT,
    FunctionTemplateID INTEGER,
    OutputName         TEXT,
    OutputValue        TEXT,
    Type               TEXT,
    FOREIGN KEY(FunctionTemplateID) REFERENCES FunctionTemplateLibrary(FunctionTemplateID)
);

-- Required parameters for each function template
CREATE TABLE IF NOT EXISTS FunctionParametersLibrary(
    FunctionParameterID INTEGER PRIMARY KEY AUTOINCREMENT,
    FunctionTemplateID  INTEGER,
    ParameterName       TEXT,
    ParameterValue      TEXT,
    Type                TEXT,
    FOREIGN KEY(FunctionTemplateID) REFERENCES FunctionTemplateLibrary(FunctionTemplateID)
);


-- ─── Performance Indexes ──────────────────────────────────────────────

-- Indexes for workflow navigation and performance
CREATE INDEX IF NOT EXISTS idx_strategy_goal ON StrategyInSession(GoalID);
CREATE INDEX IF NOT EXISTS idx_function_strategy ON FunctionInSession(StrategyID);
CREATE INDEX IF NOT EXISTS idx_function_output_function ON FunctionOutputInSession(FunctionID);
CREATE INDEX IF NOT EXISTS idx_function_params_function ON FunctionParametersInSession(FunctionID);

-- Indexes for lookup operations
CREATE INDEX IF NOT EXISTS idx_strategy_name ON StrategyInSession(StrategyName);
CREATE INDEX IF NOT EXISTS idx_function_name ON FunctionInSession(FunctionName);
CREATE INDEX IF NOT EXISTS idx_strategy_success ON StrategyInSession(StrategySuccess);
CREATE INDEX IF NOT EXISTS idx_function_success ON FunctionInSession(FunctionSuccess);
CREATE INDEX IF NOT EXISTS idx_goal_success ON GoalInSession(GoalSuccess);

-- Composite indexes for complex queries
CREATE INDEX IF NOT EXISTS idx_strategy_goal_success ON StrategyInSession(GoalID, StrategySuccess);
CREATE INDEX IF NOT EXISTS idx_function_strategy_success ON FunctionInSession(StrategyID, FunctionSuccess);
