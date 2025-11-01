# Agentic Workflow Database Integration Pattern

This document describes a generic pattern for integrating hierarchical agentic workflows with database systems for state persistence, execution tracking, and template management.

## Workflow Overview

The agentic workflow follows a hierarchical execution pattern with validation loops and database persistence at each level:

```
Goal → Strategy → Function → Validation → Success/Retry
```

## Workflow Nodes and Database Integration

### 1. Goal Definition (`GoalDefine`)
**Purpose**: Establish the high-level objective for the agentic system.

**Database Integration**:
- **Insert**: Create new goal record with pending status
- **Fields**: Goal ID, session identifier, objective description, success criteria
- **State Tracking**: NULL (pending) → 0 (failed) → 1 (success)

```sql
INSERT INTO Goals (session_id, description, criteria, status) 
VALUES (?, ?, ?, NULL);
```

### 2. Strategy Planning (`StrategyPlan`)
**Purpose**: Select and instantiate reasoning strategies to achieve the goal.

**Database Integration**:
- **Template Lookup**: Query strategy library for applicable approaches
- **Instance Creation**: Create strategy execution record linked to goal
- **Plan Storage**: Persist strategy steps and expected outcomes

```sql
-- Lookup available strategies
SELECT * FROM StrategyTemplates WHERE applicable_to = ?;

-- Create strategy instance
INSERT INTO StrategyInstances (goal_id, template_id, plan_steps, status)
VALUES (?, ?, ?, NULL);
```

### 3. Function Execution (`FunctionExecute`)
**Purpose**: Execute individual functions within the selected strategy.

**Database Integration**:
- **Parameter Resolution**: Load function parameters from templates and prior outputs
- **Execution Tracking**: Record function calls with input parameters
- **Output Storage**: Persist function results for downstream use

```sql
-- Load function template and parameters
SELECT * FROM FunctionTemplates WHERE name = ?;
SELECT * FROM FunctionParameters WHERE template_id = ?;

-- Record function execution
INSERT INTO FunctionInstances (strategy_id, template_id, status)
VALUES (?, ?, NULL);

-- Store parameters and outputs
INSERT INTO FunctionInputs (function_id, param_name, param_value) VALUES (?, ?, ?);
INSERT INTO FunctionOutputs (function_id, output_name, output_value) VALUES (?, ?, ?);
```

### 4. Validation Nodes
**Purpose**: Validate execution results and determine continuation logic.

#### Function Validation (`FunctionValidate`)
- **Success Check**: Verify function completed successfully
- **Output Validation**: Confirm outputs match expected schema
- **Status Update**: Mark function as succeeded/failed

#### Strategy Validation (`StrategyValidate`)
- **Completion Check**: Verify all strategy functions completed
- **Goal Progress**: Assess progress toward goal completion
- **Retry Logic**: Determine if strategy should retry or terminate

#### Goal Validation (`GoalValidate`)
- **Final Assessment**: Evaluate if goal criteria are met
- **Success Determination**: Mark goal as completed or failed
- **Session Closure**: Finalize workflow execution

```sql
-- Update execution status
UPDATE FunctionInstances SET status = ?, completion_time = NOW() WHERE id = ?;
UPDATE StrategyInstances SET status = ?, completion_time = NOW() WHERE id = ?;
UPDATE Goals SET status = ?, completion_time = NOW() WHERE id = ?;
```

## Database Schema Pattern

### Core Execution Tables
```sql
-- Hierarchical execution tracking
Goals                    -- Top-level objectives
├── StrategyInstances    -- Strategy executions for each goal
    ├── FunctionInstances -- Function executions within strategies
        ├── FunctionInputs   -- Input parameters for each function
        └── FunctionOutputs  -- Results produced by functions
```

### Template Libraries
```sql
-- Reusable templates and definitions
StrategyTemplates        -- Available strategy patterns
FunctionTemplates        -- Available function definitions
├── FunctionParameters   -- Required parameter schemas
└── FunctionOutputs      -- Expected output schemas
```

## Control Flow and Database Operations

### 1. Linear Progression
Normal execution flows linearly through the hierarchy with database persistence at each step:
- Goal creation → Strategy instantiation → Function execution → Validation

### 2. Retry Mechanisms
Failed validations trigger retry logic with database state management:
- **Function Retry**: Return to `FunctionExecute` with updated parameters
- **Strategy Retry**: Return to `StrategyPlan` with alternative approach
- **Goal Continuation**: Proceed to `GoalValidate` when strategy succeeds

### 3. State Persistence
Database maintains complete execution history:
- **Audit Trail**: Full record of all execution attempts
- **Recovery Support**: Ability to resume from any point
- **Analytics**: Historical data for performance optimization

## Implementation Benefits

### 1. Reliability
- **Crash Recovery**: Workflow can resume from last persisted state
- **Audit Trail**: Complete execution history for debugging
- **Consistency**: Database constraints ensure data integrity

### 2. Scalability
- **Template Reuse**: Strategy and function templates reduce redundancy
- **Parallel Execution**: Database supports concurrent workflow instances
- **Performance Optimization**: Indexes on execution status enable fast queries

### 3. Observability
- **Progress Tracking**: Real-time status monitoring through database queries
- **Performance Metrics**: Execution time and success rate analytics
- **Error Analysis**: Detailed failure tracking and root cause analysis

## Usage Patterns

### Session Management
```sql
-- Create new workflow session
INSERT INTO Sessions (created_at, status) VALUES (NOW(), 'active');

-- Track session progress
SELECT 
    g.status as goal_status,
    COUNT(s.id) as strategies_attempted,
    COUNT(f.id) as functions_executed
FROM Goals g
LEFT JOIN StrategyInstances s ON g.id = s.goal_id
LEFT JOIN FunctionInstances f ON s.id = f.strategy_id
WHERE g.session_id = ?;
```

### Template Management
```sql
-- Register new function template
INSERT INTO FunctionTemplates (name, description, strategy_type)
VALUES ('data_processor', 'Processes input data', 'analytical');

-- Define function parameters
INSERT INTO FunctionParameters (template_id, name, type, required)
VALUES (?, 'input_data', 'json', true);
```

### Execution Monitoring
```sql
-- Monitor active workflows
SELECT 
    session_id,
    goal_description,
    current_strategy,
    last_activity
FROM WorkflowStatus 
WHERE status = 'active'
ORDER BY last_activity DESC;
```

## Best Practices

1. **Transaction Management**: Use database transactions for atomic state updates
2. **Index Strategy**: Create indexes on status fields and foreign keys for performance
3. **Cleanup Procedures**: Implement retention policies for historical execution data
4. **Schema Evolution**: Design schema to accommodate new template types and validation logic
5. **Error Handling**: Store detailed error information for debugging and improvement

This pattern provides a robust foundation for building agentic systems that require reliable execution tracking, template-based reusability, and comprehensive observability.
