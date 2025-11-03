#!/usr/bin/env python3
"""
Strategic Pattern Implementation for Agentic Architecture

Based on analysis of current goal-strategy-functions-validations flow and the 18 high-confidence
questions from questions.py, this module defines 6 core strategic patterns as reusable,
composable function blocks.

Architecture Alignment:
- Leverages existing FUNCTION_MAP structure in function_library.py
- Compatible with template-driven strategy execution in templates.py  
- Integrates with workflow_nodes.py goal-strategy-functions flow
- Extends current function categories (search, filter, analyze, etc.)

Strategic Pattern Design:
- Each pattern is a composite function that orchestrates multiple atomic functions
- Patterns can be chained and combined for complex multi-strategy execution
- Maintains existing parameter/output schema compatibility
- Provides confidence scoring and explanation tracking
"""

# =============================================================================
# STRATEGIC PATTERN DEFINITIONS
# =============================================================================

def create_specification_lookup_strategy():
    """
    PATTERN 1: SPECIFICATION LOOKUP STRATEGY
    
    Handles direct product lookups by specifications, codes, and dimensions.
    Covers questions: 23, 34, 37, 66, 75, 77 (6 questions)
    
    Reusable Function Block Components:
    - Product Code Resolution (direct lookup or family normalization)
    - Specification Filtering (pressure, temperature, dimension criteria)  
    - Attribute Extraction (deterministic parsing of specs)
    - Result Assembly (structured output formatting)
    """
    return {
        "pattern_name": "SPECIFICATION_LOOKUP",
        "description": "Direct product specification queries with filtering",
        "function_sequence": [
            # Phase 1: Product Resolution
            {
                "name": "Resolve Product Identity", 
                "functions": ["Extract Product Number", "Normalize Product Number"],
                "mode": "conditional"  # Try direct first, then normalize if needed
            },
            # Phase 2: Data Retrieval  
            {
                "name": "Retrieve Product Data",
                "functions": ["Search Products", "Query Database"],
                "mode": "fallback"  # Try structured search first, then SQL if needed
            },
            # Phase 3: Specification Processing
            {
                "name": "Process Specifications", 
                "functions": ["Extract Attributes", "Filter Items"],
                "mode": "sequential"
            },
            # Phase 4: Result Assembly
            {
                "name": "Assemble Results",
                "functions": ["Compare Items", "Analyze With LLM"],
                "mode": "conditional"  # Compare if multiple items, analyze for insights
            }
        ],
        "parameters": {
            "product_code": {"source": "user_query", "extraction": "product_pattern"},
            "filter_criteria": {"source": "user_query", "extraction": "spec_requirements"},
            "output_format": {"default": "detailed_specs"}
        },
        "success_criteria": {
            "min_results": 1,
            "confidence_threshold": 0.7,
            "required_fields": ["product_code", "specifications"]
        }
    }

def create_application_search_strategy():
    """
    PATTERN 2: APPLICATION SEARCH STRATEGY
    
    Searches by use case, industry, environment, and application requirements.
    Covers questions: 8, 10, 14, 22, 24, 47, 82 (7 questions)
    
    Reusable Function Block Components:
    - Application Context Extraction (use case identification)
    - Requirements Analysis (pressure, temp, chemical resistance)
    - Product Family Filtering (applications field search)
    - Recommendation Ranking (suitability scoring)
    """
    return {
        "pattern_name": "APPLICATION_SEARCH", 
        "description": "Use-case driven product recommendations",
        "function_sequence": [
            # Phase 1: Context Understanding
            {
                "name": "Extract Application Context",
                "functions": ["Semantic Search", "Suggest Keywords"],
                "mode": "parallel"  # Extract both semantic meaning and keywords
            },
            # Phase 2: Requirement Analysis
            {
                "name": "Analyze Requirements",
                "functions": ["Extract Attributes", "Get Metadata"], 
                "mode": "parallel"  # Parse requirements and get domain context
            },
            # Phase 3: Product Discovery
            {
                "name": "Discover Suitable Products",
                "functions": ["Search Products", "Filter Items"],
                "mode": "sequential"  # Search then filter by requirements
            },
            # Phase 4: Recommendation Generation
            {
                "name": "Generate Recommendations",
                "functions": ["Aggregate Data", "Analyze With LLM"],
                "mode": "sequential"  # Group similar products then analyze
            }
        ],
        "parameters": {
            "application_type": {"source": "user_query", "extraction": "use_case_pattern"},
            "environment": {"source": "user_query", "extraction": "environment_terms"}, 
            "requirements": {"source": "user_query", "extraction": "technical_specs"}
        },
        "success_criteria": {
            "min_results": 1,
            "confidence_threshold": 0.6,
            "required_explanations": ["suitability_reason", "application_match"]
        }
    }

def create_standards_certification_strategy():
    """
    PATTERN 3: STANDARDS & CERTIFICATION STRATEGY
    
    Searches by compliance standards, certifications, and regulatory requirements.
    Covers questions: 14, 20, 81, 82 (4 questions)
    
    Reusable Function Block Components:
    - Standard Recognition (EN, ISO, FDA, DNV identification)
    - Compliance Filtering (construction_details standards search)
    - Certification Validation (cross-reference with product specs)
    - Compliance Analysis (detailed standard explanations)
    """
    return {
        "pattern_name": "STANDARDS_CERTIFICATION",
        "description": "Standards compliance and certification queries", 
        "function_sequence": [
            # Phase 1: Standard Identification
            {
                "name": "Identify Standards",
                "functions": ["Extract Attributes", "Lookup Standard"],
                "mode": "parallel"  # Extract mentioned standards and lookup details
            },
            # Phase 2: Compliance Search
            {
                "name": "Search Compliant Products", 
                "functions": ["Query Database", "Filter Items"],
                "mode": "sequential"  # SQL search construction_details then filter
            },
            # Phase 3: Certification Analysis
            {
                "name": "Analyze Certifications",
                "functions": ["Get Metadata", "Compare Items"], 
                "mode": "parallel"  # Get certification context and compare products
            },
            # Phase 4: Compliance Validation
            {
                "name": "Validate Compliance",
                "functions": ["Analyze With LLM"],
                "mode": "single"  # LLM explains compliance details and implications
            }
        ],
        "parameters": {
            "standards": {"source": "user_query", "extraction": "standard_codes"},
            "certification_type": {"source": "user_query", "extraction": "cert_keywords"},
            "compliance_level": {"default": "full_compliance"}
        },
        "success_criteria": {
            "min_results": 1,
            "confidence_threshold": 0.8,
            "required_fields": ["standards_list", "compliance_status"]
        }
    }

def create_material_construction_strategy():
    """
    PATTERN 4: MATERIAL & CONSTRUCTION STRATEGY
    
    Searches by material properties, construction details, and compatibility.
    Covers questions: 25, 36, 75, 79 (4 questions)
    
    Reusable Function Block Components:
    - Material Identification (rubber types, composites, metals)
    - Construction Analysis (inner/outer tube, reinforcement)
    - Compatibility Assessment (chemical, temperature, oil compatibility)
    - Material Comparison (trade-offs between material choices)
    """
    return {
        "pattern_name": "MATERIAL_CONSTRUCTION",
        "description": "Material properties and construction analysis",
        "function_sequence": [
            # Phase 1: Material Context
            {
                "name": "Analyze Material Requirements",
                "functions": ["Extract Attributes", "Semantic Search"],
                "mode": "parallel"  # Extract material needs and search semantically
            },
            # Phase 2: Construction Search
            {
                "name": "Search by Construction", 
                "functions": ["Query Database", "Filter Items"],
                "mode": "sequential"  # Search construction_details then filter results
            },
            # Phase 3: Compatibility Analysis
            {
                "name": "Assess Compatibility",
                "functions": ["Get Related Items", "Compare Items"],
                "mode": "parallel"  # Find compatible products and compare materials
            },
            # Phase 4: Material Analysis
            {
                "name": "Analyze Material Properties",
                "functions": ["Analyze With LLM"],
                "mode": "single"  # Explain material properties and suitability
            }
        ],
        "parameters": {
            "material_type": {"source": "user_query", "extraction": "material_keywords"},
            "construction_focus": {"source": "user_query", "extraction": "construction_terms"},
            "compatibility_media": {"source": "user_query", "extraction": "media_types"}
        },
        "success_criteria": {
            "min_results": 1, 
            "confidence_threshold": 0.7,
            "required_explanations": ["material_properties", "compatibility_assessment"]
        }
    }

def create_comparative_analysis_strategy():
    """
    PATTERN 5: COMPARATIVE ANALYSIS STRATEGY
    
    Compares products, standards, or specifications side-by-side.
    Covers questions: 11, 36 (2 questions but fundamental for many use cases)
    
    Reusable Function Block Components:
    - Multi-Product Resolution (handle "product A vs B" queries)
    - Specification Extraction (get comparable attributes)  
    - Side-by-Side Comparison (structured comparison tables)
    - Trade-off Analysis (LLM explains pros/cons and recommendations)
    """
    return {
        "pattern_name": "COMPARATIVE_ANALYSIS",
        "description": "Side-by-side product and specification comparison",
        "function_sequence": [
            # Phase 1: Entity Resolution
            {
                "name": "Resolve Comparison Items",
                "functions": ["Extract Product Number", "Search Products"],
                "mode": "sequential"  # Extract multiple products then search for each
            },
            # Phase 2: Attribute Extraction
            {
                "name": "Extract Comparable Attributes",
                "functions": ["Extract Attributes", "Get Metadata"],
                "mode": "parallel"  # Get product attributes and comparison schema
            },
            # Phase 3: Comparison Analysis
            {
                "name": "Perform Comparison",
                "functions": ["Compare Items", "Filter Items"],
                "mode": "sequential"  # Compare then filter to key differences
            },
            # Phase 4: Insight Generation
            {
                "name": "Generate Insights",
                "functions": ["Analyze With LLM"],
                "mode": "single"  # Explain differences, trade-offs, recommendations
            }
        ],
        "parameters": {
            "comparison_items": {"source": "user_query", "extraction": "product_list"},
            "comparison_aspects": {"source": "user_query", "extraction": "comparison_criteria"},
            "output_style": {"default": "side_by_side_with_recommendations"}
        },
        "success_criteria": {
            "min_items": 2,
            "confidence_threshold": 0.8,
            "required_outputs": ["comparison_table", "key_differences", "recommendations"]
        }
    }

def create_multi_criteria_filtering_strategy():
    """
    PATTERN 6: MULTI-CRITERIA FILTERING STRATEGY
    
    Handles complex queries with multiple constraints and requirements.
    Used as a meta-strategy that can combine other patterns.
    
    Reusable Function Block Components:
    - Criteria Decomposition (break complex query into parts)
    - Multi-Stage Filtering (apply filters in optimal order)
    - Result Aggregation (combine results from multiple search paths)
    - Confidence Scoring (rank results by match quality)
    """
    return {
        "pattern_name": "MULTI_CRITERIA_FILTERING",
        "description": "Complex multi-constraint product selection",
        "function_sequence": [
            # Phase 1: Query Decomposition
            {
                "name": "Decompose Criteria",
                "functions": ["Extract Attributes", "Suggest Keywords"], 
                "mode": "parallel"  # Extract all types of criteria
            },
            # Phase 2: Multi-Path Search
            {
                "name": "Execute Multi-Path Search",
                "functions": ["Search Products", "Semantic Search", "Query Database"],
                "mode": "parallel"  # Try multiple search approaches
            },
            # Phase 3: Progressive Filtering
            {
                "name": "Apply Progressive Filters",
                "functions": ["Filter Items", "Aggregate Data"],
                "mode": "sequential"  # Filter then aggregate by relevance
            },
            # Phase 4: Result Synthesis
            {
                "name": "Synthesize Results",
                "functions": ["Compare Items", "Analyze With LLM"],
                "mode": "sequential"  # Compare top candidates then analyze
            }
        ],
        "parameters": {
            "criteria_types": {"source": "user_query", "extraction": "all_criteria"},
            "priority_order": {"source": "user_query", "extraction": "importance_signals"},
            "result_count": {"default": 10}
        },
        "success_criteria": {
            "min_results": 1,
            "confidence_threshold": 0.6,
            "required_explanations": ["match_reasoning", "criteria_satisfaction"]
        }
    }

# =============================================================================
# PATTERN ORCHESTRATION FRAMEWORK
# =============================================================================

class StrategyPatternOrchestrator:
    """
    Orchestrates strategic patterns within your existing goal-strategy-functions flow.
    
    Integrates with:
    - templates.py: Adds new strategy templates for each pattern
    - function_library.py: Uses existing function implementations
    - workflow_nodes.py: Fits into strategy execution phase
    - strategy_testing.py: Can be enabled/disabled for testing
    """
    
    def __init__(self):
        self.patterns = {
            "SPECIFICATION_LOOKUP": create_specification_lookup_strategy(),
            "APPLICATION_SEARCH": create_application_search_strategy(), 
            "STANDARDS_CERTIFICATION": create_standards_certification_strategy(),
            "MATERIAL_CONSTRUCTION": create_material_construction_strategy(),
            "COMPARATIVE_ANALYSIS": create_comparative_analysis_strategy(),
            "MULTI_CRITERIA_FILTERING": create_multi_criteria_filtering_strategy()
        }
    
    def get_pattern_templates_for_library(self):
        """Generate strategy templates compatible with templates.py format."""
        
        strategy_templates = []
        
        for pattern_id, pattern in self.patterns.items():
            # Convert pattern to templates.py strategy format
            function_names = []
            for phase in pattern["function_sequence"]:
                if phase["mode"] == "parallel":
                    # Use [Func1 || Func2] syntax for parallel execution
                    parallel_group = " || ".join(phase["functions"])
                    function_names.append(f"[{parallel_group}]")
                elif phase["mode"] == "conditional":
                    # Use first function, fallback to second if needed
                    function_names.extend(phase["functions"])
                else:
                    # Sequential execution
                    function_names.extend(phase["functions"])
            
            plan_steps = ", ".join(function_names)
            
            strategy_template = (
                pattern["pattern_name"],
                "pattern",  # New strategy type
                pattern["description"],
                plan_steps
            )
            strategy_templates.append(strategy_template)
        
        return strategy_templates
    
    def execute_pattern(self, pattern_id: str, user_query: str, context: dict = None):
        """
        Execute a strategic pattern with your existing function execution framework.
        
        This would integrate with workflow_nodes.py function execution logic.
        """
        if pattern_id not in self.patterns:
            return False, f"Unknown pattern: {pattern_id}"
        
        pattern = self.patterns[pattern_id]
        
        # This would call into your existing function execution framework
        # from workflow_nodes.py node_function_execute()
        
        results = {}
        for phase in pattern["function_sequence"]:
            phase_name = phase["name"]
            functions = phase["functions"] 
            mode = phase["mode"]
            
            if mode == "parallel":
                # Execute functions in parallel (your existing parallel support)
                phase_results = self._execute_parallel_functions(functions, context)
            elif mode == "sequential": 
                # Execute functions sequentially
                phase_results = self._execute_sequential_functions(functions, context)
            elif mode == "conditional":
                # Execute with fallback logic
                phase_results = self._execute_conditional_functions(functions, context)
            else:
                # Single function execution
                phase_results = self._execute_single_function(functions[0], context)
            
            results[phase_name] = phase_results
            # Update context for next phase
            context.update(phase_results)
        
        return True, results
    
    def _execute_parallel_functions(self, functions, context):
        """Execute functions in parallel - integrates with your existing parallel support."""
        # This would call your existing parallel execution logic from workflow_nodes.py
        pass
    
    def _execute_sequential_functions(self, functions, context):
        """Execute functions sequentially.""" 
        # This would call your existing sequential execution logic
        pass
    
    def _execute_conditional_functions(self, functions, context):
        """Execute functions with conditional/fallback logic."""
        # Try first function, fallback to second if needed
        pass
    
    def _execute_single_function(self, function_name, context):
        """Execute single function."""
        # This would call your existing function execution from FUNCTION_MAP
        pass

# =============================================================================
# INTEGRATION WITH EXISTING ARCHITECTURE  
# =============================================================================

def integrate_patterns_with_existing_system():
    """
    Shows how to integrate strategic patterns with your current implementation.
    
    Integration Points:
    1. Add pattern strategies to templates.py
    2. Add pattern orchestration to workflow_nodes.py
    3. Add pattern selection to strategy planning
    4. Add pattern configuration to strategy_testing.py
    """
    
    orchestrator = StrategyPatternOrchestrator()
    
    # 1. Get strategy templates for templates.py
    pattern_templates = orchestrator.get_pattern_templates_for_library()
    
    # 2. Add to your existing strategies list in templates.py
    example_integration = """
    # Add these to your strategies list in templates.py:
    
    strategies = [
        # ... your existing strategies ...
        
        # Strategic Patterns (6 new strategies)
        (
            "SPECIFICATION_LOOKUP_PATTERN",
            "pattern", 
            "Direct product specification queries with filtering",
            "[Extract Product Number || Normalize Product Number], [Search Products || Query Database], Extract Attributes, Filter Items, [Compare Items || Analyze With LLM]"
        ),
        (
            "APPLICATION_SEARCH_PATTERN", 
            "pattern",
            "Use-case driven product recommendations",
            "[Semantic Search || Suggest Keywords], [Extract Attributes || Get Metadata], Search Products, Filter Items, Aggregate Data, Analyze With LLM"
        ),
        # ... other patterns ...
    ]
    """
    
    # 3. Add pattern selection logic to strategy planning
    strategy_selection_logic = """
    # In workflow_nodes.py node_strategy_plan():
    
    def select_strategic_pattern(user_query: str) -> str:
        # Pattern detection based on question analysis
        if re.search(r'\\b(pressure|temperature|specification|bar|mpa|°c)\\b', user_query.lower()):
            return "SPECIFICATION_LOOKUP_PATTERN"
        elif re.search(r'\\b(application|use|environment|chemical|food|boiling)\\b', user_query.lower()):
            return "APPLICATION_SEARCH_PATTERN" 
        elif re.search(r'\\b(standard|en\\s*\\d+|iso|fda|dnv|certified|approved)\\b', user_query.lower()):
            return "STANDARDS_CERTIFICATION_PATTERN"
        elif re.search(r'\\b(material|rubber|construction|smooth|compatibility)\\b', user_query.lower()):
            return "MATERIAL_CONSTRUCTION_PATTERN"
        elif re.search(r'\\b(compare|difference|vs|versus)\\b', user_query.lower()):
            return "COMPARATIVE_ANALYSIS_PATTERN"
        else:
            return "MULTI_CRITERIA_FILTERING_PATTERN"  # Default for complex queries
    """
    
    # 4. Configuration in strategy_testing.py
    config_integration = """
    # Add to strategy_testing.py:
    
    STRATEGY_TESTING = {
        # ... your existing strategies ...
        
        # Strategic Patterns
        "SPECIFICATION_LOOKUP_PATTERN": True,
        "APPLICATION_SEARCH_PATTERN": True, 
        "STANDARDS_CERTIFICATION_PATTERN": True,
        "MATERIAL_CONSTRUCTION_PATTERN": True,
        "COMPARATIVE_ANALYSIS_PATTERN": True,
        "MULTI_CRITERIA_FILTERING_PATTERN": True,
    }
    """
    
    return {
        "pattern_templates": pattern_templates,
        "integration_example": example_integration,
        "selection_logic": strategy_selection_logic,
        "config_integration": config_integration
    }

# =============================================================================
# EXAMPLE: CHAINING AND COMBINING PATTERNS
# =============================================================================

def example_pattern_combinations():
    """
    Examples of how patterns can be chained and combined for complex queries.
    """
    
    examples = {
        "complex_specification_query": {
            "query": "I need a hose rated for 400 bar that works with chemicals and meets EN 857 standard",
            "pattern_chain": [
                "SPECIFICATION_LOOKUP_PATTERN",  # Find 400+ bar hoses
                "APPLICATION_SEARCH_PATTERN",    # Filter for chemical compatibility  
                "STANDARDS_CERTIFICATION_PATTERN" # Verify EN 857 compliance
            ],
            "execution_mode": "sequential_filtering"  # Each pattern narrows results
        },
        
        "comparative_application_query": {
            "query": "Compare KAPPAFLEX 1 and KAPPAFLEX 2K for excavator applications",
            "pattern_chain": [
                "COMPARATIVE_ANALYSIS_PATTERN",   # Compare the two products
                "APPLICATION_SEARCH_PATTERN"     # Analyze excavator suitability
            ],
            "execution_mode": "analysis_enhancement"  # Second pattern enhances first
        },
        
        "multi_criteria_recommendation": {
            "query": "Recommend a blue water hose in 3/4\" that's food safe and DNV certified", 
            "pattern_chain": [
                "MULTI_CRITERIA_FILTERING_PATTERN"  # Handles all criteria simultaneously
            ],
            "sub_patterns": [
                "SPECIFICATION_LOOKUP_PATTERN",    # Size and color requirements
                "STANDARDS_CERTIFICATION_PATTERN", # Food safety and DNV
                "APPLICATION_SEARCH_PATTERN"       # Water use case
            ],
            "execution_mode": "integrated_multi_criteria"
        }
    }
    
    return examples

if __name__ == "__main__":
    # Demonstrate pattern integration
    integration = integrate_patterns_with_existing_system()
    
    print("STRATEGIC PATTERNS FOR AGENTIC ARCHITECTURE")
    print("=" * 60)
    print()
    
    orchestrator = StrategyPatternOrchestrator()
    
    print("Available Patterns:")
    for pattern_id, pattern in orchestrator.patterns.items():
        print(f"  {pattern_id}: {pattern['description']}")
    
    print()
    print("Integration with Current Architecture:")
    print("- 6 reusable strategic patterns")
    print("- Compatible with existing goal-strategy-functions flow")
    print("- Supports parallel and sequential execution")
    print("- Chainable for complex multi-criteria queries")
    print("- Configurable via strategy_testing.py")
    
    print()
    examples = example_pattern_combinations()
    print("Example Pattern Combinations:")
    for name, example in examples.items():
        print(f"  {name}: {example['query']}")
        print(f"    Patterns: {' → '.join(example['pattern_chain'])}")
        print(f"    Mode: {example['execution_mode']}")
        print()