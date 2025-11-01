# Generic Agentic Reasoning System

A flexible, domain-agnostic agentic reasoning framework built on LangGraph. This system uses a hierarchical **Goal → Strategy → Function** workflow to process complex queries through intelligent multi-agent reasoning.

## 🎯 Architecture

```
User Query
    ↓
Goal Definition (parse intent)
    ↓
Strategy Planning (select reasoning approach)
    ↓
Function Execution (execute actions, can be parallel)
    ↓
Multi-level Validation (function → strategy → goal)
    ↓
Final Answer
```

## 🚀 Features

- **Hierarchical Workflow**: Three-level execution hierarchy (Goal → Strategy → Function)
- **Parallel Execution**: Support for concurrent function execution with batching
- **Template Library**: Reusable strategy and function templates
- **Database Integration**: Track execution state, templates, and history
- **Validation Loops**: Multi-level validation with retry mechanisms
- **LLM Integration**: Powered by language models for intelligent reasoning
- **Vector Search**: Semantic search capabilities for finding relevant information
- **Debug Modes**: Configurable verbosity levels (0-4) for development

## 📋 Prerequisites

```bash
# Python 3.9+
python --version

# Required packages
pip install langgraph langchain openai anthropic  # or other LLM providers
pip install chromadb  # for vector storage
pip install sqlite3   # usually built-in
```

## 🔧 Installation

1. **Clone or copy the Layer_2 directory**

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**:
```bash
# Set your LLM API keys
export OPENAI_API_KEY="your-key-here"
# or
export ANTHROPIC_API_KEY="your-key-here"

# Optional: Configure debug level
export DEBUG_LEVEL=2  # 0=silent, 1=minimal, 2=normal, 3=detailed, 4=verbose
```

## 📁 Project Structure

```
Layer_2/
├── agentic_reasoning/
│   ├── config/           # Configuration files
│   │   ├── constants.py  # System constants
│   │   ├── debug_config.py
│   │   └── session_config.py
│   ├── db/              # Database schemas and migrations
│   ├── logic/           # Core reasoning logic
│   │   ├── state_graph.py        # LangGraph workflow definition
│   │   ├── workflow_nodes.py     # Goal/Strategy/Function nodes
│   │   ├── function_library.py   # Executable functions
│   │   ├── templates.py          # Strategy/function templates
│   │   ├── llm_helpers.py        # LLM integration
│   │   ├── vector_helpers.py     # Vector search
│   │   └── database_manager.py   # Database operations
│   └── pipelines/       # Pre-built reasoning pipelines
├── data/                # Data storage (CSV exports, databases, etc.)
├── docs/                # Documentation and diagrams
├── tests/               # Unit and integration tests
└── main.py             # Entry point

```

## 🎮 Usage

### Basic Usage

```python
#!/usr/bin/env python3
from agentic_reasoning.config.session_config import get_default_session_state, get_workflow_config
from agentic_reasoning.logic.state_graph import get_graph
from agentic_reasoning.logic.templates import populate_template_libraries

# Initialize
user_query = "Your question here"
init_state = get_default_session_state(query=user_query)
workflow_config = get_workflow_config()

# Setup template libraries
populate_template_libraries()

# Execute
final_state = get_graph().invoke(init_state, config=workflow_config)

# Results
print(final_state['answer'])
```

### Running the Example

```bash
cd Layer_2
python main.py
```

Edit `main.py` to customize your query:
```python
# In main.py, line ~50
user_query = "Your domain-specific query"
```

## 🔌 Integration Guide

### 1. Define Domain-Specific Functions

Create functions for your domain in `agentic_reasoning/logic/function_library.py`:

```python
def your_custom_function(param1: str, param2: int) -> dict:
    """
    Description of what this function does.
    
    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2
        
    Returns:
        Dictionary with results
    """
    # Your implementation
    return {"result": "data"}
```

### 2. Create Strategy Templates

Define reasoning strategies in `agentic_reasoning/logic/templates.py`:

```python
{
    "strategyName": "YourStrategy",
    "goal": "What this strategy achieves",
    "functions": [
        {"name": "function1", "description": "Step 1"},
        {"name": "function2", "description": "Step 2"}
    ],
    "applicableWhen": "When to use this strategy"
}
```

### 3. Connect Your Database

Update database configuration in your initialization:

```python
# Point to your database
db_path = "path/to/your/database.db"

# Define your schema
# Use the database_manager to handle connections
```

### 4. Configure LLM Provider

In `agentic_reasoning/logic/llm_helpers.py`, configure your preferred LLM:

```python
# OpenAI
model = ChatOpenAI(model="gpt-4", temperature=0)

# Anthropic
model = ChatAnthropic(model="claude-3-sonnet-20240229", temperature=0)

# Local models (Ollama, etc.)
model = YourLocalModel(...)
```

## 🎛️ Configuration

### Debug Levels

Set in `main.py` or via environment variable:

```python
set_debug_level(2)  # 0-4
```

- **0 = SILENT**: No debug output
- **1 = MINIMAL**: Only major workflow steps
- **2 = NORMAL**: Standard progress indicators (recommended)
- **3 = DETAILED**: Function parameters and outputs
- **4 = VERBOSE**: All debug information

### Workflow Configuration

Modify `agentic_reasoning/config/session_config.py`:

```python
def get_workflow_config():
    return {
        "configurable": {
            "thread_id": "your-thread-id",
            # Add your custom configuration
        }
    }
```

## 📊 Example Workflows

### Simple Query Flow

```
Query: "Find product ABC"
  ↓
Goal: "Retrieve product information for ABC"
  ↓
Strategy: "Database Lookup"
  ↓
Functions: [query_database("ABC")]
  ↓
Answer: Product details
```

### Complex Multi-Step Flow

```
Query: "Compare product A with product B"
  ↓
Goal: "Provide comparative analysis of A vs B"
  ↓
Strategy: "Multi-Product Comparison"
  ↓
Functions: [
  get_product("A"),
  get_product("B"),
  compare_specifications(A, B),
  generate_summary(comparison)
]
  ↓
Answer: Detailed comparison
```

## 🧪 Testing

```bash
# Run tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_workflow.py
```

## 📝 Best Practices

1. **Keep Functions Atomic**: Each function should do one thing well
2. **Use Descriptive Names**: Clear function and strategy names improve LLM reasoning
3. **Validate Outputs**: Always validate function outputs before passing to next step
4. **Handle Errors Gracefully**: Implement proper error handling and fallbacks
5. **Log Executions**: Use the database to track execution history
6. **Test Strategies**: Test each strategy independently before integration
7. **Configure Retries**: Set appropriate retry limits for validation loops

## 🔍 Troubleshooting

### LLM Not Responding
- Check API keys are set correctly
- Verify network connectivity
- Check rate limits

### Functions Not Found
- Ensure functions are registered in the function library
- Check function names match template references

### Database Errors
- Verify database path is correct
- Check schema is initialized
- Ensure proper permissions

## 🤝 Contributing

This is a generic framework designed to be extended. To adapt for your domain:

1. Implement domain-specific functions in `function_library.py`
2. Create strategy templates for common query patterns
3. Configure database schema for your data model
4. Set up vector embeddings for your documents/data
5. Test with real-world queries

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

Built with:
- **LangGraph**: State machine orchestration
- **LangChain**: LLM integration
- **ChromaDB**: Vector storage
- **SQLite**: State persistence
