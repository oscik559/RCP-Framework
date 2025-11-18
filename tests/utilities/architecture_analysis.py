"""
System Architecture Analysis and Insights

Generated from:
- Database inspection (harvested.db, agentic.db schemas)
- Main.py execution walkthrough
- Current strategy testing configuration
- Data coverage analysis

Date: November 18, 2025
"""

import json

ARCHITECTURE_ANALYSIS = {
    "database_layer": {
        "harvested_db": {
            "purpose": "Product data warehouse - immutable, populated by extraction layers",
            "tables": {
                "categories": {
                    "rows": 2,
                    "data": ["HÖGTRYCKSSLANG (KAPITEL 1:1)", "PRESSKOPPLINGAR (KAPITEL 4:2)"],
                    "note": "Only 2 categories currently harvested - high-pressure hoses & press couplings"
                },
                "product_families": {
                    "rows": 168,
                    "distribution": {
                        "HÖGTRYCKSSLANG": 69,
                        "PRESSKOPPLINGAR": 99
                    },
                    "key_fields": ["family_code", "name", "construction_details (JSON)", "applications"],
                    "fts": "YES - Full-text search enabled on family_code, name, applications"
                },
                "products": {
                    "rows": 1628,
                    "all_have_specs": True,
                    "spec_format": "JSON stored as string",
                    "example_spec_keys": ["Artikelnr", "ID mm", "ID tum", "YD mm", "Arb.tr. MPa", "Böjradie mm", "Vikt kg/m"],
                    "configuration_types": ["STANDARD", "REEL"],
                    "note": "1628 SKUs total across 168 families"
                },
                "product_knowledge": {
                    "rows": 0,
                    "note": "Empty - not yet populated. Expected to contain assembly, standards, general knowledge"
                },
                "page_regions": {
                    "rows": 66,
                    "purpose": "Track header/footer regions for exclusion during extraction"
                }
            },
            "capabilities": [
                "✅ Query by product code (e.g., '1110-00-06')",
                "✅ Search by family name (e.g., 'ISOBAR 10')",
                "✅ Full-text search on applications",
                "✅ JSON spec extraction (flexible, no schema enforcement)",
                "⚠️  No category/family hierarchy traversal yet (could be added)",
                "❌ No product knowledge base (future enhancement)"
            ]
        },
        "agentic_db": {
            "purpose": "Session state & workflow orchestration (volatile, cleared between sessions)",
            "tables": [
                "strategies - loaded from templates.py",
                "functions - loaded from templates.py",
                "parameter_schemas - input definitions",
                "output_schemas - output definitions",
                "session_data - query + strategy attempts",
                "goal_data - parsed goals",
                "function_results - execution logs",
                "parallel_execution_groups - parallel task batches (for PARALLEL ENHANCED LOOKUP)",
                "session_index - session tracking"
            ],
            "lifecycle": "Recreated on each main.py execution (initialize → populate templates → execute → clear)",
            "note": "Transient state DB for workflow execution - does NOT store persistent data"
        }
    },
    "strategy_layer": {
        "current_state": {
            "total_strategies_defined": 12,
            "active_strategy": "DIRECT SPECIFICATION LOOKUP",
            "testing_mode": "SINGLE_STRATEGY",
            "redundant_strategies": [
                "SIMPLE LOOKUP",
                "ENHANCED LOOKUP",
                "VISUAL LAYOUT",
                "PRODUCT COMPARISON",
                "SMART RECOMMENDATION",
                "HIERARCHICAL NAVIGATION",
                "SPECIFICATION ANALYSIS",
                "ASSEMBLED SPECIFICATION LOOKUP"
            ],
            "note": "Current config only enables DIRECT SPECIFICATION LOOKUP for testing"
        },
        "workflow_flow": {
            "step_1": "GoalDefine - Parse user query into structured goal",
            "step_2": "StrategyPlan - Select strategy from library (agentic.db)",
            "step_3": "FunctionExecute - Run functions sequentially or parallel",
            "step_4": "FunctionValidate - Check each function output",
            "step_5": "StrategyValidate - Check if strategy plan completed",
            "step_6": "GoalValidate - Final validation + LLM synthesis",
            "step_7": "Done - Return final answer"
        },
        "parallel_execution": {
            "supported": True,
            "mechanism": "PARALLEL ENHANCED LOOKUP uses [Func1 || Func2] syntax in plan steps",
            "storage": "parallel_execution_groups table in agentic.db",
            "use_case": "Speed optimization for independent functions (e.g., search + normalize in parallel)"
        }
    },
    "function_execution_layer": {
        "current_active_functions": [
            {
                "name": "Extract Product Number",
                "id": 1,
                "type": "extract",
                "input": "query string",
                "output": "product code (e.g., '1110-00-06')",
                "llm_needed": True,
                "status": "working"
            },
            {
                "name": "Query Database",
                "id": 2,
                "type": "search",
                "input": "product_code, query_type, table, fields, joins, etc.",
                "output": "list of matching products",
                "llm_needed": False,
                "status": "working"
            },
            {
                "name": "Extract Attributes",
                "id": 3,
                "type": "extract",
                "input": "list of product records",
                "output": "extracted_data (flattened specs + metadata)",
                "llm_needed": False,
                "status": "working",
                "note": "Deterministic - parses JSON specs, joins family data"
            },
            {
                "name": "Analyze With LLM",
                "id": 4,
                "type": "analyze",
                "input": "extracted_data, question",
                "output": "formatted analysis",
                "llm_needed": True,
                "status": "working",
                "modes": ["direct (small data)", "assembly (large data via temp.db)"]
            }
        ],
        "llm_integration": {
            "model": "llama3.2:latest (via Ollama)",
            "invocations_per_query": "2-3 (vary by strategy)",
            "failure_retry": "3 attempts with exponential backoff",
            "cost_optimization": "Only 1-2 strategies need LLM (Extract + Analyze), others deterministic"
        }
    },
    "data_flow_example": {
        "query": "What do you know about the product 1110-00-06?",
        "execution_trace": {
            "1_goal_define": {
                "input": "full query",
                "llm_call": "Extract structured goal",
                "output": "goal_id=1, goal_type='product_lookup'"
            },
            "2_strategy_plan": {
                "input": "goal_id",
                "logic": "Query agentic.db for matching strategy",
                "output": "strategy_id=1, name='DIRECT SPECIFICATION LOOKUP', plan='Extract Product Number, Query Database, Extract Attributes, Analyze With LLM'"
            },
            "3_function_1_extract_product_number": {
                "function": "Extract Product Number",
                "input": "What do you know about the product 1110-00-06?",
                "llm_call": "Yes - extract product ID from query",
                "output": "1110-00-06"
            },
            "4_function_2_query_database": {
                "function": "Query Database",
                "input": "product_code='1110-00-06', table='products'",
                "db_call": "SELECT * FROM products WHERE product_code='1110-00-06'",
                "db_used": "harvested.db",
                "output": "product_record (1 row with JSON specs)"
            },
            "5_function_3_extract_attributes": {
                "function": "Extract Attributes",
                "input": "product_record",
                "logic": "Parse JSON specs + join with family_id to get family_name",
                "db_call": "SELECT name, family_code FROM product_families WHERE id=16",
                "db_used": "harvested.db",
                "output": {
                    "product_code": "1110-00-06",
                    "family_name": "ISOBAR 10",
                    "specifications": {
                        "ID mm": "10,0",
                        "ID tum": "3/8\"",
                        "YD mm": "14,8",
                        "Arb.tr. MPa": "10,0"
                    }
                }
            },
            "6_function_4_analyze_with_llm": {
                "function": "Analyze With LLM",
                "input": "extracted_data + original question",
                "llm_call": "Yes - format specs as readable answer",
                "output": "Formatted response with all specs and context"
            },
            "7_goal_validate": {
                "input": "final_answer + goal",
                "llm_call": "Yes - validate answer matches goal",
                "output": "confidence=0.8, goal_ok=True"
            }
        },
        "databases_accessed": ["agentic.db (templates)", "harvested.db (product data)"],
        "temp_db": "Could be used for large dataset assembly (currently unused)",
        "total_execution_time": "~2-3 seconds (mostly LLM latency)"
    },
    "integration_points": {
        "langchain": "LLM invocations via llm_helpers.py",
        "langgraph": "State graph orchestration via state_graph.py",
        "sqlite": "Database access via Layer_2_Agentic/db/connection.py",
        "ollama": "Local LLM inference (http://127.0.0.1:11434)",
        "chroma": "Vector index for semantic search (referenced but not yet used)"
    },
    "current_limitations": {
        "data_coverage": [
            "❌ Only 2 categories populated (need more PDFs harvested)",
            "❌ product_knowledge empty (no assembly, standards, general knowledge)",
            "⚠️  No vector embeddings for semantic search yet",
            "⚠️  No category hierarchy traversal"
        ],
        "strategy_implementation": [
            "❌ 11 of 12 strategies are not implemented (templates only)",
            "✅ Only DIRECT SPECIFICATION LOOKUP works end-to-end",
            "⚠️  PARALLEL ENHANCED LOOKUP defined but not tested",
            "❌ CONTEXTUAL PRODUCT SEARCH blocked on LLM + semantic search setup"
        ],
        "performance": [
            "⚠️  Slow due to LLM latency (Ollama local inference)",
            "⚠️  No caching for repeated queries",
            "⚠️  No query optimization (could use indexes better)"
        ]
    },
    "recommendations_for_future": {
        "immediate_priorities": [
            "1️⃣ Implement core functions in function_library.py:",
            "   - direct_specification_lookup() ✅ Already working",
            "   - contextual_product_search() - needs semantic search setup",
            "   - technical_calculation() - pure math, can implement quickly",
            "   - standard_and_compliance_lookup() - similar to direct lookup",
            "   - knowledge_base_rag() - for procedural/general knowledge",
            "",
            "2️⃣ Populate product_knowledge table:",
            "   - Extract assembly instructions from PDFs",
            "   - Extract standard definitions",
            "   - Create knowledge base for FAQ questions",
            "",
            "3️⃣ Set up semantic search:",
            "   - Create embeddings for all products",
            "   - Store in Chroma vector DB",
            "   - Enable contextual_product_search strategy"
        ],
        "optimization_opportunities": [
            "- Add caching layer for product lookups",
            "- Implement parallel execution in PARALLEL ENHANCED LOOKUP",
            "- Add query optimization (use indexes on frequent searches)",
            "- Move to cloud LLM for faster inference (vs local Ollama)",
            "- Pre-compute common aggregations (e.g., 'products by pressure')"
        ],
        "architecture_improvements": [
            "- Consider separating agentic.db into persistent config + transient state",
            "- Add query logging/analytics for strategy refinement",
            "- Implement result caching with TTL",
            "- Add monitoring/alerting for function failures"
        ]
    },
    "test_question_mapping": {
        "covered_by_direct_specification_lookup": [
            "Q63: What is the maximum temperature for hose 1071-00-16?",
            "Q64: Which socket fits 1118-12-16?",
            "Q70: What is ISO bar?",
            "Q72: Can I use environmental oil in 1105-63?",
            "Q74: Which hose for 380 bar?",
            "~30+ product lookup questions"
        ],
        "will_be_covered_by_contextual_search": [
            "Q5: What hoses for boiling water?",
            "Q7: Which hose + sleeve for excavator?",
            "Q21: Hoses for chemicals?",
            "~35+ application/recommendation questions"
        ],
        "will_be_covered_by_technical_calculation": [
            "Q47: Flow 150 L/min → hose size?",
            "Q48: Flow 20 L/min → suction/return size?",
            "Q49: 100 L/min + 200 mbar drop → size?",
            "~5 hydraulic math questions"
        ],
        "will_be_covered_by_standards_lookup": [
            "Q17: EN 857 standard?",
            "Q71: Standards for hydraulic hose?",
            "Q78: DNV classified hoses?",
            "~5 standard/compliance questions"
        ],
        "will_be_covered_by_knowledge_base": [
            "Q77: How to install shell sleeve?",
            "Q2: What is your role?",
            "~4 procedural/system questions"
        ]
    }
}


if __name__ == "__main__":
    print(json.dumps(ARCHITECTURE_ANALYSIS, indent=2, ensure_ascii=False))
