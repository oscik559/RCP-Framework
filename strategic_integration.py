#!/usr/bin/env python3
"""
Strategic Pattern Integration for Layer_2-Agentic

This module provides concrete implementations showing how to integrate the 6 strategic patterns
with your existing goal-strategy-functions-validations flow in Layer_2-Agentic.

Based on Analysis of Your Current Architecture:
✅ templates.py: Strategy templates with function sequences  
✅ function_library.py: 29 functions in FUNCTION_MAP with (params) -> (success, results) interface
✅ workflow_nodes.py: Goal → Strategy → Function execution with parallel support
✅ strategy_testing.py: Enable/disable strategies for testing
✅ Existing "ASSEMBLED SPECIFICATION LOOKUP" strategy already working

Strategic Pattern Approach:
Instead of 18+ individual strategies, create 6 meta-strategies that:
1. Reuse your existing 29 functions in creative combinations
2. Add intelligent parameter routing between functions  
3. Support multi-strategy chaining for complex queries
4. Maintain your existing parallel execution capabilities
"""

# =============================================================================
# STRATEGIC PATTERN TEMPLATES FOR templates.py
# =============================================================================

def get_strategic_pattern_templates():
    """
    Returns strategic pattern templates in your existing templates.py format.
    These can be directly added to the strategies list.
    """
    
    strategic_patterns = [
        # Pattern 1: Specification Lookup (Questions: 23, 34, 37, 66, 75, 77)
        (
            "SPECIFICATION_LOOKUP_PATTERN",
            "pattern",
            "Direct product specification queries with intelligent filtering and assembly. Handles product codes, dimensions, pressure ratings, temperature specs.",
            # Function sequence: Extract → Search → Filter → Assemble → Analyze  
            "Extract Product Number, Search Products, Filter Items, Extract Attributes, Assemble Product Data, Analyze With LLM"
        ),
        
        # Pattern 2: Application Search (Questions: 8, 10, 14, 22, 24, 47, 82)
        (
            "APPLICATION_SEARCH_PATTERN", 
            "pattern",
            "Use-case driven product recommendations with semantic search and requirement matching. Handles applications, environments, industries.",
            # Function sequence: Semantic search → Requirements → Filter → Aggregate → Analyze
            "Semantic Search, Extract Attributes, Search Products, Filter Items, Aggregate Data, Analyze With LLM"
        ),
        
        # Pattern 3: Standards & Certification (Questions: 14, 20, 81, 82)
        (
            "STANDARDS_CERTIFICATION_PATTERN",
            "pattern", 
            "Standards compliance and certification queries. Handles EN, ISO, FDA, DNV, and other regulatory requirements.",
            # Function sequence: Standard lookup → Database query → Filter → Compare → Analyze
            "Lookup Standard, Query Database, Filter Items, Extract Attributes, Compare Items, Analyze With LLM"
        ),
        
        # Pattern 4: Material & Construction (Questions: 25, 36, 75, 79)
        (
            "MATERIAL_CONSTRUCTION_PATTERN",
            "pattern",
            "Material properties and construction analysis. Handles rubber types, construction details, compatibility assessment.",
            # Function sequence: Semantic search → Database query → Extract → Compare → Analyze
            "Semantic Search, Query Database, Extract Attributes, Get Related Items, Compare Items, Analyze With LLM"
        ),
        
        # Pattern 5: Comparative Analysis (Questions: 11, 36)
        (
            "COMPARATIVE_ANALYSIS_PATTERN",
            "pattern",
            "Side-by-side product and specification comparison with trade-off analysis and recommendations.",
            # Function sequence: Extract products → Search → Extract attributes → Compare → Analyze
            "Extract Product Number, Search Products, Extract Attributes, Compare Items, Analyze With LLM"
        ),
        
        # Pattern 6: Multi-Criteria Filtering (Complex queries)
        (
            "MULTI_CRITERIA_FILTERING_PATTERN",
            "pattern",
            "Complex multi-constraint product selection with progressive filtering and confidence scoring.",
            # Parallel search then sequential refinement
            "[Semantic Search || Search Products || Query Database], Filter Items, Aggregate Data, Extract Attributes, Analyze With LLM"
        ),
        
        # Meta-Pattern: Chained Strategy Execution
        (
            "STRATEGIC_CHAIN_PATTERN",
            "meta",
            "Executes multiple strategic patterns in sequence for complex multi-faceted queries.",
            # This would be handled by special orchestration logic
            "Pattern Router, Pattern Chain Executor, Result Synthesizer"
        )
    ]
    
    return strategic_patterns

# =============================================================================
# PARAMETER ROUTING AND FUNCTION ENHANCEMENT
# =============================================================================

def get_enhanced_function_parameters():
    """
    Enhanced parameter schemas for strategic pattern execution.
    These extend your existing params dictionary in templates.py.
    """
    
    enhanced_params = {
        # Enhanced Search Products for pattern support
        "Search Products": [
            ("category", "", "string"),
            ("keywords", "Input", "string"),  # Auto-extract from user query
            ("filters", "{}", "json"),
            ("limit", "50", "integer"),
            # Pattern-specific enhancements
            ("pattern_context", "", "string"),  # Which pattern is calling this
            ("extraction_mode", "auto", "string"),  # How to extract keywords
            ("result_format", "standard", "string")  # How to format results
        ],
        
        # Enhanced Filter Items for intelligent filtering
        "Filter Items": [
            ("items", "[]", "json"),
            ("filters", "{}", "json"), 
            ("filter_mode", "AND", "string"),
            # Pattern-specific enhancements
            ("filter_strategy", "progressive", "string"),  # How to apply filters
            ("confidence_scoring", "true", "boolean"),  # Score match quality
            ("explanation_mode", "detailed", "string")  # Provide filter explanations
        ],
        
        # Enhanced Analyze With LLM for pattern-aware analysis
        "Analyze With LLM": [
            ("task", "advice", "string"),
            ("extracted_data", "", "json"),
            ("Assembled Data", "", "json"), 
            ("question", "Input", "string"),
            # Pattern-specific enhancements
            ("analysis_pattern", "", "string"),  # Which pattern triggered this
            ("context_type", "product_query", "string"),  # Type of analysis needed
            ("output_style", "comprehensive", "string"),  # How to format response
            ("confidence_threshold", "0.7", "number")  # Minimum confidence for answers
        ],
    }
    
    return enhanced_params

# =============================================================================
# PATTERN SELECTION INTELLIGENCE 
# =============================================================================

def create_pattern_selector():
    """
    Intelligent pattern selection based on question analysis from questions.py.
    
    Uses the 18 high-confidence questions to train pattern recognition.
    """
    
    pattern_selectors = {
        "SPECIFICATION_LOOKUP_PATTERN": {
            "triggers": [
                r"maximum.*pressure.*\d+.*bar|working.*pressure|pressure.*rating",
                r"temperature.*\d+.*°c|maximum.*temperature|temperature.*rating", 
                r"hose.*\d{4}-\d{2}-\d{2}|product.*code.*\d+|article.*number",
                r"dimension.*\d+.*mm|\d+.*inch|diameter.*\d+",
                r"bar.*working|mpa.*rating|specifications.*\d+"
            ],
            "example_questions": [
                "What is the maximum working pressure for this hose at 100 °C?",
                "What is the maximum temperature for hose 1071-00-16?", 
                "Which hose should I use if I have 380bar in the machine?",
                "Which hydraulic hoses are rated for more than 300 bar working pressure?"
            ]
        },
        
        "APPLICATION_SEARCH_PATTERN": {
            "triggers": [
                r"boiling.*water|hot.*water|water.*application",
                r"excavator.*application|heavy.*machinery|construction.*equipment",
                r"chemical.*resistance|chemical.*compatibility|chemical.*use",
                r"food.*use|food.*approved|food.*grade|fda.*approved",
                r"vibration.*resistance|high.*pressure.*vibration"
            ],
            "example_questions": [
                "What hoses can be used for boiling water?",
                "Which hydraulic hose and sleeve should I get for a particular excavator?", 
                "What hoses can be used for chemicals?",
                "Which products are approved for food use?"
            ]
        },
        
        "STANDARDS_CERTIFICATION_PATTERN": {
            "triggers": [
                r"en.*857.*standard|iso.*\d+|din.*\d+",
                r"dnv.*classified|dnv.*certified|dnv.*approved",
                r"fda.*approved|food.*approved|food.*grade",
                r"standard.*compliance|meets.*standard|certified.*for"
            ],
            "example_questions": [
                "Do you have hoses that meet the EN 857 standard?",
                "Which hoses are DNV classified?",
                "Which hoses are FDA approved for food use?"
            ]
        },
        
        "MATERIAL_CONSTRUCTION_PATTERN": {
            "triggers": [
                r"natural.*rubber|nbr.*material|synthetic.*rubber",
                r"smooth.*outer.*casing|smooth.*surface|outer.*cover",
                r"construction.*details|material.*properties|inner.*tube",
                r"environmental.*oil|oil.*compatibility|material.*compatibility"
            ],
            "example_questions": [
                "Natural rubber hoses?", 
                "Is there a hose with a smooth outer casing?",
                "Can I use environmental oil in 1105-63?"
            ]
        },
        
        "COMPARATIVE_ANALYSIS_PATTERN": {
            "triggers": [
                r"difference.*between.*and|compare.*vs|versus.*product",
                r"2sn.*vs.*2sc|difference.*2sn.*2sc",
                r"product.*a.*vs.*product.*b|compare.*product.*a.*b"
            ],
            "example_questions": [
                "What is the difference between product A and B?",
                "What is the difference between a 2SN and 2SC hose?"
            ]
        },
        
        "MULTI_CRITERIA_FILTERING_PATTERN": {
            "triggers": [
                r"blue.*water.*hose.*3/4|color.*dimension.*application",
                r"multiple.*requirements|several.*criteria|complex.*specification",
                r"need.*and.*also|requirement.*plus.*requirement"
            ],
            "example_questions": [
                "I need a blue water hose in 3/4\"?",
                "Do you have a product that can withstand both high pressure and vibrations?"
            ]
        }
    }
    
    return pattern_selectors

def select_strategic_pattern(user_query: str) -> tuple[str, float]:
    """
    Select the most appropriate strategic pattern for a user query.
    
    Returns:
        tuple: (pattern_name, confidence_score)
    """
    import re
    
    selectors = create_pattern_selector()
    pattern_scores = {}
    
    query_lower = user_query.lower()
    
    for pattern_name, selector in selectors.items():
        score = 0.0
        matches = 0
        
        for trigger in selector["triggers"]:
            if re.search(trigger, query_lower):
                matches += 1
                score += 0.3  # Base score per trigger match
        
        # Boost score based on number of triggers matched
        if matches > 0:
            score += min(matches * 0.2, 0.6)  # Bonus for multiple matches
            pattern_scores[pattern_name] = min(score, 1.0)
    
    if not pattern_scores:
        # Default to multi-criteria filtering for unmatched queries
        return "MULTI_CRITERIA_FILTERING_PATTERN", 0.5
    
    # Return highest scoring pattern
    best_pattern = max(pattern_scores.items(), key=lambda x: x[1])
    return best_pattern

# =============================================================================
# INTEGRATION WITH EXISTING WORKFLOW_NODES.PY
# =============================================================================

def create_pattern_aware_strategy_selection():
    """
    Shows how to integrate pattern selection into your existing node_strategy_plan().
    """
    
    strategy_integration_code = '''
    # In workflow_nodes.py node_strategy_plan() function:
    
    def enhanced_strategy_selection(user_query: str, existing_strategies: list) -> str:
        """Enhanced strategy selection with strategic pattern support."""
        
        # 1. Try strategic pattern matching first  
        pattern_name, confidence = select_strategic_pattern(user_query)
        
        if confidence > 0.7:
            logger.info(f"Selected strategic pattern: {pattern_name} (confidence: {confidence})")
            return pattern_name
        
        # 2. Fallback to existing strategy selection logic
        # Your current strategy selection logic here...
        
        # 3. If no good match, use multi-criteria pattern as safe default
        if confidence > 0.4:
            logger.info(f"Using strategic pattern with medium confidence: {pattern_name}")  
            return pattern_name
        else:
            logger.info("Using existing strategy selection logic")
            return your_existing_strategy_selection_logic(user_query, existing_strategies)
    '''
    
    return strategy_integration_code

# =============================================================================
# PATTERN CHAINING AND COMBINATION EXAMPLES
# =============================================================================

def create_pattern_chaining_examples():
    """
    Real examples of how patterns can be chained for complex queries.
    """
    
    examples = {
        "sequential_filtering_chain": {
            "description": "Each pattern narrows down results progressively",
            "query": "I need a hose rated for 400 bar that works with chemicals and meets EN 857 standard",
            "execution": [
                {
                    "pattern": "SPECIFICATION_LOOKUP_PATTERN",
                    "purpose": "Find hoses rated ≥400 bar", 
                    "functions": ["Search Products", "Filter Items", "Extract Attributes"],
                    "output": "high_pressure_hoses"
                },
                {
                    "pattern": "APPLICATION_SEARCH_PATTERN",
                    "purpose": "Filter for chemical compatibility",
                    "functions": ["Filter Items", "Query Database", "Extract Attributes"],
                    "input": "high_pressure_hoses",
                    "output": "chemical_compatible_hoses"
                },
                {
                    "pattern": "STANDARDS_CERTIFICATION_PATTERN", 
                    "purpose": "Verify EN 857 compliance",
                    "functions": ["Lookup Standard", "Filter Items", "Analyze With LLM"],
                    "input": "chemical_compatible_hoses", 
                    "output": "final_recommendations"
                }
            ]
        },
        
        "parallel_enhancement_chain": {
            "description": "Patterns run in parallel then results are combined",
            "query": "Compare KAPPAFLEX 1 and KAPPAFLEX 2K for excavator applications with DNV certification",
            "execution": [
                {
                    "patterns": ["COMPARATIVE_ANALYSIS_PATTERN", "APPLICATION_SEARCH_PATTERN", "STANDARDS_CERTIFICATION_PATTERN"],
                    "mode": "parallel",
                    "purpose": "Get comprehensive analysis from multiple angles",
                    "combination": "intersect_and_enhance"
                }
            ]
        },
        
        "adaptive_pattern_routing": {
            "description": "Pattern selection adapts based on intermediate results",
            "query": "What's the best hose for my application?", 
            "execution": [
                {
                    "pattern": "MULTI_CRITERIA_FILTERING_PATTERN",
                    "purpose": "Initial broad search and requirement extraction",
                    "adaptive_routing": {
                        "if_specific_product_found": "SPECIFICATION_LOOKUP_PATTERN",
                        "if_application_focused": "APPLICATION_SEARCH_PATTERN", 
                        "if_comparison_needed": "COMPARATIVE_ANALYSIS_PATTERN"
                    }
                }
            ]
        }
    }
    
    return examples

# =============================================================================
# CONFIGURATION FOR STRATEGY_TESTING.PY
# =============================================================================

def get_strategy_testing_configuration():
    """
    Configuration entries for your strategy_testing.py file.
    """
    
    config = {
        # Strategic Patterns - can be individually enabled/disabled for testing
        "SPECIFICATION_LOOKUP_PATTERN": True,
        "APPLICATION_SEARCH_PATTERN": True,
        "STANDARDS_CERTIFICATION_PATTERN": True, 
        "MATERIAL_CONSTRUCTION_PATTERN": True,
        "COMPARATIVE_ANALYSIS_PATTERN": True,
        "MULTI_CRITERIA_FILTERING_PATTERN": True,
        
        # Meta-patterns
        "STRATEGIC_CHAIN_PATTERN": False,  # Advanced chaining - enable when ready
        
        # Pattern behavior configuration
        "PATTERN_CONFIDENCE_THRESHOLD": 0.7,  # Minimum confidence to use pattern
        "PATTERN_FALLBACK_ENABLED": True,     # Fallback to existing strategies
        "PATTERN_CHAINING_ENABLED": False,    # Enable pattern chaining (advanced)
        "PATTERN_PARALLEL_EXECUTION": True,   # Use parallel execution in patterns
    }
    
    return config

# =============================================================================
# DEMONSTRATION AND TESTING
# =============================================================================

def test_pattern_selection():
    """Test pattern selection with real questions from questions.py."""
    
    test_questions = [
        "What hoses can be used for boiling water?",
        "Which hydraulic hoses are rated for more than 300 bar working pressure?", 
        "Do you have hoses that meet the EN 857 standard?",
        "Natural rubber hoses?",
        "What is the difference between a 2SN and 2SC hose?",
        "I need a blue water hose in 3/4\"?",
        "What is the maximum temperature for hose 1071-00-16?",
        "Which hoses are DNV classified?"
    ]
    
    print("STRATEGIC PATTERN SELECTION TESTING")
    print("=" * 50)
    
    for question in test_questions:
        pattern, confidence = select_strategic_pattern(question)
        print(f"Q: {question}")
        print(f"   → Pattern: {pattern}")
        print(f"   → Confidence: {confidence:.2f}")
        print()

def demonstrate_integration():
    """Demonstrate how patterns integrate with existing architecture."""
    
    print("INTEGRATION DEMONSTRATION")
    print("=" * 40)
    
    print("1. Strategic Pattern Templates:")
    patterns = get_strategic_pattern_templates()
    for name, target, desc, plan in patterns:
        print(f"   {name}: {desc}")
        print(f"   Functions: {plan}")
        print()
    
    print("2. Enhanced Function Parameters:")
    enhanced = get_enhanced_function_parameters()
    for func_name, params in enhanced.items():
        print(f"   {func_name}: {len(params)} enhanced parameters")
    
    print()
    print("3. Strategy Testing Configuration:")
    config = get_strategy_testing_configuration()
    enabled_patterns = [k for k, v in config.items() if v and k.endswith("_PATTERN")]
    print(f"   {len(enabled_patterns)} patterns available for testing")
    
    print()
    print("4. Pattern Chaining Examples:")
    examples = create_pattern_chaining_examples() 
    for name, example in examples.items():
        print(f"   {name}: {example['description']}")

if __name__ == "__main__":
    print("STRATEGIC PATTERNS INTEGRATION WITH LAYER_2-AGENTIC")
    print("=" * 60)
    print()
    
    test_pattern_selection()
    print()
    demonstrate_integration()
    
    print()
    print("NEXT STEPS FOR IMPLEMENTATION:")
    print("1. Add strategic pattern templates to templates.py")
    print("2. Enhance function parameters in templates.py") 
    print("3. Add pattern selection to workflow_nodes.py")
    print("4. Configure pattern testing in strategy_testing.py")
    print("5. Test individual patterns before enabling chaining")
    print("6. Gradually enable advanced features (chaining, adaptive routing)")