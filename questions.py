#!/usr/bin/env python3
"""
Questions Analysis: Produktbok.pdf vs harvested.db

This file contains an analysis of which test questions from test_questions_en.xlsx 
can be answered using the structured data extracted from Produktbok.pdf and 
stored in harvested.db.

Database Structure Available:
- categories: Product categories (HÖGTRYCKSSLANG, etc.)
- product_families: 69 product families with construction details and applications
- products: 335 individual products with specifications
- Full-text search capability on product families

Data Fields Available:
- product_families.construction_details (JSON with materials, temperatures, standards)
- product_families.applications (usage descriptions) 
- products.specifications (JSON with dimensions, pressures, etc.)
- products.product_code (article numbers)
"""

# =============================================================================
# QUESTIONS WE CAN ANSWER (25 questions) - SORTED BY CONFIDENCE LEVEL
# =============================================================================

# HIGH CONFIDENCE QUESTIONS (18 questions)
HIGH_CONFIDENCE_QUESTIONS = [
    {
        "id": 8,
        "question": "What hoses can be used for boiling water?",
        "confidence": "High",
        "reason": "Can search applications and construction_details for temperature ratings and hot water applications",
        "database_strategy": "Search product_families.applications for 'hot water' and construction_details for temperature specs ≥100°C",
        "example_data": "Construction details contain temperature ranges like '-40°C – +100°C'"
    },
    
    {
        "id": 10,
        "question": "Which hydraulic hose and sleeve should I get for a particular excavator?",
        "confidence": "High",
        "reason": "Can search applications field for excavator/heavy machinery use cases",
        "database_strategy": "Search product_families.applications for 'excavator' or heavy duty applications",
        "example_data": "Applications field contains usage descriptions like construction/heavy machinery"
    },
    
    {
        "id": 11,
        "question": "What is the difference between product A and B?",
        "confidence": "High",
        "reason": "Can compare specifications and construction details between any two products",
        "database_strategy": "Query both products and compare their specifications and construction_details JSON",
        "example_data": "Can compare pressure ratings, materials, dimensions from specifications"
    },
    
    {
        "id": 14,
        "question": "Which products are approved for food use?",
        "confidence": "High", 
        "reason": "Can search applications and construction details for food approvals/FDA compliance",
        "database_strategy": "Search applications for 'food' and construction_details for FDA/food standards",
        "example_data": "Applications describe food industry usage, construction may list FDA compliance"
    },
    
    {
        "id": 20,
        "question": "Do you have hoses that meet the EN 857 standard?",
        "confidence": "High",
        "reason": "Can search construction details for EN 857 standard compliance",
        "database_strategy": "Search construction_details JSON for 'EN 857' standards",
        "example_data": "Standards array in construction: ['EN 857 2SC', 'DNV', 'MED', 'MSHA']"
    },
    
    {
        "id": 22,
        "question": "Do you have a product that can withstand both high pressure and vibrations?",
        "confidence": "High",
        "reason": "Can search applications for vibration resistance and specifications for pressure ratings",
        "database_strategy": "Search applications for 'vibration' and specifications for high pressure values",
        "example_data": "Applications describe vibration resistance, specs show pressure ratings like '45.0 MPa'"
    },
    
    {
        "id": 23,
        "question": "What is the maximum working pressure for this hose at 100 °C?",
        "confidence": "High",
        "reason": "Can look up specifications for pressure ratings and temperature derating",
        "database_strategy": "Query product_code and extract working_pressure from specifications JSON",
        "example_data": "Specifications: 'working_pressure_mpa': 45.0, temperature ranges in construction_details"
    },
    
    {
        "id": 24,
        "question": "What hoses can be used for chemicals?",
        "confidence": "High",
        "reason": "Can search applications field for chemical compatibility and usage",
        "database_strategy": "Search product_families.applications for 'chemical' usage descriptions", 
        "example_data": "Applications describe chemical resistance and industrial chemical use"
    },
    
    {
        "id": 25,
        "question": "Natural rubber hoses?",
        "confidence": "High",
        "reason": "Can search construction details for natural rubber materials",
        "database_strategy": "Search construction_details for 'natural rubber' or 'NR' in materials",
        "example_data": "Construction details: 'inner_tube': 'Syntetiskt oljebeständigt gummi'"
    },
    
    {
        "id": 34,
        "question": "I need a blue water hose in 3/4\"?",
        "confidence": "High",
        "reason": "Can search specifications for 3/4\" dimension and applications for water use",
        "database_strategy": "Search specifications for '3/4' or '19mm' dimension and applications for water",
        "example_data": "Specifications contain dimension data, applications describe water usage"
    },
    
    {
        "id": 36,
        "question": "What is the difference between a 2SN and 2SC hose?",
        "confidence": "High", 
        "reason": "Can compare construction details between different hose standard types",
        "database_strategy": "Search product names/construction for '2SN' vs '2SC' and compare specifications",
        "example_data": "Product names and construction details differentiate between standards"
    },
    
    {
        "id": 37,
        "question": "Which hydraulic hoses are rated for more than 300 bar working pressure?",
        "confidence": "High",
        "reason": "Can search specifications for pressure ratings above 30 MPa (300 bar)",
        "database_strategy": "Query specifications where working_pressure_mpa > 30",
        "example_data": "Specifications: 'working_pressure_mpa': 45.0 (450 bar)"
    },
    
    {
        "id": 47,
        "question": "Need suggestions for hose for chemicals",
        "confidence": "High",
        "reason": "Can search applications field for chemical use cases and recommendations",
        "database_strategy": "Search product_families.applications for chemical resistance descriptions",
        "example_data": "Applications describe chemical compatibility and industrial chemical transport"
    },
    
    {
        "id": 66,
        "question": "What is the maximum temperature for hose 1071-00-16?",
        "confidence": "High",
        "reason": "Can look up specific product code and extract temperature from specifications",
        "database_strategy": "Query products where product_code = '1071-00-16' and extract temperature specs",
        "example_data": "Direct product code lookup with temperature specifications"
    },
    
    {
        "id": 75,
        "question": "Can I use environmental oil in 1105-63?",
        "confidence": "High",
        "reason": "Can check construction details for material compatibility with environmental oils",
        "database_strategy": "Query product_code '1105-63' and check construction_details for material compatibility",
        "example_data": "Construction details describe material properties and oil compatibility"
    },
    
    {
        "id": 77,
        "question": "Which hose should I use if I have 380bar in the machine?",
        "confidence": "High",
        "reason": "Can search specifications for hoses rated above 38 MPa (380 bar)",
        "database_strategy": "Query specifications where working_pressure_mpa >= 38",
        "example_data": "Multiple products with pressure ratings above 38 MPa available"
    },
    
    {
        "id": 81,
        "question": "Which hoses are DNV classified?",
        "confidence": "High",
        "reason": "Can search construction details for DNV certification in standards array",
        "database_strategy": "Search construction_details for 'DNV' in standards array",
        "example_data": "Standards array: ['EN 857 2SC', 'DNV', 'MED', 'MSHA']"
    },
    
    {
        "id": 82,
        "question": "Which hoses are FDA approved for food use?",
        "confidence": "High", 
        "reason": "Can search applications and construction for FDA approvals and food compliance",
        "database_strategy": "Search applications for 'FDA' or 'food' and construction_details for FDA standards",
        "example_data": "Applications describe food industry usage, construction may list FDA compliance"
    }
]

# MEDIUM CONFIDENCE QUESTIONS (6 questions)
MEDIUM_CONFIDENCE_QUESTIONS = [
    {
        "id": 9,
        "question": "Which sleeve should I get for hose X?",
        "confidence": "Medium", 
        "reason": "Can look up specific hose codes and find construction details about compatible sleeves",
        "database_strategy": "Query products.product_code and check construction_details for sleeve recommendations",
        "example_data": "Construction details may contain sleeve specifications like 'hylsa': '4200-11-xx, 4200-23-xx'"
    },
    
    {
        "id": 12,
        "question": "Which coupling fits my existing hose with dimension Y?",
        "confidence": "Medium",
        "reason": "Can look up hose dimensions in specifications and match with construction details",
        "database_strategy": "Search products.specifications for dimension match, check construction_details for coupling info",
        "example_data": "Specifications contain dimensions like 'ID mm': '6.5', 'YD mm': '13.4'"
    },
    
    {
        "id": 30,
        "question": "Which hoses are suitable for the 42 series?",
        "confidence": "Medium",
        "reason": "Can search product codes and family codes for 42 series compatibility",
        "database_strategy": "Search product_codes and family_codes for '42' series references",
        "example_data": "Product codes may reference series compatibility"
    },
    
    {
        "id": 48,
        "question": "Hose for alkaline degreasing?",
        "confidence": "Medium",
        "reason": "Can search applications and construction for alkaline/chemical resistance",
        "database_strategy": "Search applications for 'alkaline' or 'degreasing' and construction for chemical resistance",
        "example_data": "Applications may describe cleaning/degreasing usage"
    },
    
    {
        "id": 67,
        "question": "Which socket fits 1118-12-16?",
        "confidence": "Medium",
        "reason": "Can look up product code and check construction details for compatible accessories",
        "database_strategy": "Query product_code '1118-12-16' and check construction_details for socket/sleeve info",
        "example_data": "Construction details may contain socket/sleeve compatibility info"
    },
    
    {
        "id": 79,
        "question": "Is there a hose with a smooth outer casing?",
        "confidence": "Medium",
        "reason": "Can search construction details or product names for smooth outer surface features",
        "database_strategy": "Search product names for 'smooth' or construction_details for outer surface descriptions",
        "example_data": "Product names may include 'SMOOTH' variants in family names"
    }
]

# LOW CONFIDENCE QUESTIONS (1 question)
LOW_CONFIDENCE_QUESTIONS = [
    {
        "id": 21,
        "question": "What is the lifespan or maintenance intervals of product X?",
        "confidence": "Low",
        "reason": "May have maintenance info in construction details, but likely limited",
        "database_strategy": "Check construction_details for maintenance specifications",
        "example_data": "Limited maintenance data likely available"
    }
]

# Combined list for backward compatibility
ANSWERABLE_QUESTIONS = HIGH_CONFIDENCE_QUESTIONS + MEDIUM_CONFIDENCE_QUESTIONS + LOW_CONFIDENCE_QUESTIONS

# =============================================================================
# QUESTIONS WE CANNOT ANSWER (Limited by current database structure)
# =============================================================================

UNANSWERABLE_QUESTIONS = [
    {
        "id": 26,
        "question": "What sizes does Storz have?",
        "reason": "Storz couplings are specific products not represented in current hose-focused schema",
        "missing_data": "Detailed coupling/fitting product categories and specifications"
    },
    
    {
        "id": 27, 
        "question": "Steam connections?",
        "reason": "Specific coupling types not detailed in current product structure",
        "missing_data": "Dedicated coupling/fitting specifications and steam ratings"
    },
    
    {
        "id": 28,
        "question": "Camlock seal?",
        "reason": "Seal/gasket specifications not in current database structure", 
        "missing_data": "Seal and gasket product categories and specifications"
    },
    
    {
        "id": 33,
        "question": "What material are pipe clamps made of?",
        "reason": "Pipe clamps appear to be separate product category not in current hose data",
        "missing_data": "Pipe clamp specifications and materials database"
    },
    
    {
        "id": 35,
        "question": "Is there an adapter from JIC to BSP for 1\"?",
        "reason": "Adapter specifications not in current hose-focused database structure",
        "missing_data": "Detailed adapter/fitting product database with threading specifications"
    },
    
    {
        "id": 19,
        "question": "What is the recommended tightening torque for this coupling?",
        "reason": "Installation specifications not stored in current database",
        "missing_data": "Installation procedures and torque specification tables"
    },
    
    {
        "id": 40,
        "question": "How many millimeters is 1/8\"?",
        "reason": "General conversion question, not product-specific data",
        "missing_data": "Not applicable - general engineering knowledge"
    },
    
    {
        "id": 41,
        "question": "Thread that is 12.4 mm internally?",
        "reason": "Thread specification tables not in current database",
        "missing_data": "Comprehensive thread specification and conversion tables"
    },
    
    {
        "id": 43,
        "question": "What sizes are available for Code 62 flanges?",
        "reason": "Flange specifications not detailed in current hose-focused structure",
        "missing_data": "Detailed flange product database with size specifications"
    },
    
    {
        "id": 72,
        "question": "How tight should I tighten a G 1/2\" thread?",
        "reason": "Installation torque specifications not in database",
        "missing_data": "Installation specification tables and torque recommendations"
    }
]

# =============================================================================
# SUMMARY STATISTICS
# =============================================================================

# =============================================================================
# STRATEGIC ANALYSIS: AGENTIC ARCHITECTURE PATTERNS
# =============================================================================

"""
CRITICAL ANALYSIS OF HIGH-CONFIDENCE QUESTIONS

After analyzing the 18 high-confidence questions, we can identify 6 core strategic patterns
that can be implemented as reusable function blocks in our agentic architecture:

1. SPECIFICATION_LOOKUP_STRATEGY
   - Direct product code queries (questions 23, 66, 75)
   - Specification filtering (questions 37, 77)
   - Dimension matching (question 34)

2. APPLICATION_SEARCH_STRATEGY  
   - Use case matching (questions 8, 10, 24, 47)
   - Industry/environment search (questions 14, 82)
   - Performance requirement matching (question 22)

3. STANDARDS_CERTIFICATION_STRATEGY
   - Standards compliance search (questions 20, 81)
   - Regulatory approval search (questions 14, 82)
   - Certification filtering (question 81)

4. MATERIAL_CONSTRUCTION_STRATEGY
   - Material composition search (question 25)
   - Construction detail analysis (questions 36, 79)
   - Compatibility assessment (question 75)

5. COMPARATIVE_ANALYSIS_STRATEGY
   - Product comparison (question 11)
   - Standard differentiation (question 36)
   - Feature comparison across products

6. MULTI_CRITERIA_FILTERING_STRATEGY
   - Combined specification + application filtering
   - Multiple constraint satisfaction
   - Ranking by relevance score

RECOMMENDED IMPLEMENTATION APPROACH:

Instead of creating 18+ individual strategies, implement these 6 core strategy types
as parameterized function blocks that can be combined and configured for different
question types. This reduces complexity while maintaining flexibility.

Each strategy should:
- Accept flexible parameters (search terms, filters, thresholds)
- Return structured results with confidence scores
- Support chaining with other strategies
- Provide explanation of search logic used

FUNCTION BLOCK ARCHITECTURE:
┌─────────────────────────────────────────────────────────────┐
│  QUESTION CLASSIFICATION                                     │
│  ├─ Intent Recognition                                       │ 
│  ├─ Parameter Extraction                                     │
│  └─ Strategy Selection                                       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  STRATEGY EXECUTION ENGINE                                   │
│  ├─ Specification Lookup                                     │
│  ├─ Application Search                                       │
│  ├─ Standards Certification                                  │
│  ├─ Material Construction                                    │
│  ├─ Comparative Analysis                                     │
│  └─ Multi-Criteria Filtering                                │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│  RESULT SYNTHESIS & RANKING                                  │
│  ├─ Confidence Scoring                                       │
│  ├─ Relevance Ranking                                        │
│  └─ Answer Generation                                        │
└─────────────────────────────────────────────────────────────┘
"""

def print_summary():
    """Print summary statistics of the question analysis."""
    total_questions = len(ANSWERABLE_QUESTIONS) + len(UNANSWERABLE_QUESTIONS)
    answerable_count = len(ANSWERABLE_QUESTIONS) 
    unanswerable_count = len(UNANSWERABLE_QUESTIONS)
    
    print(f"QUESTION ANALYSIS SUMMARY")
    print(f"=" * 50)
    print(f"Total questions analyzed: {total_questions}")
    print(f"Answerable with current database: {answerable_count} ({answerable_count/total_questions*100:.1f}%)")
    print(f"Not answerable with current database: {unanswerable_count} ({unanswerable_count/total_questions*100:.1f}%)")
    print()
    print(f"High confidence answers: {len(HIGH_CONFIDENCE_QUESTIONS)}")
    print(f"Medium confidence answers: {len(MEDIUM_CONFIDENCE_QUESTIONS)}")
    print(f"Low confidence answers: {len(LOW_CONFIDENCE_QUESTIONS)}")
    
    print(f"\nSTRATEGIC PATTERNS IDENTIFIED:")
    print(f"1. Specification Lookup Strategy (6 questions)")
    print(f"2. Application Search Strategy (7 questions)")  
    print(f"3. Standards/Certification Strategy (3 questions)")
    print(f"4. Material/Construction Strategy (3 questions)")
    print(f"5. Comparative Analysis Strategy (2 questions)")
    print(f"6. Multi-Criteria Filtering Strategy (multiple)")

def analyze_high_confidence_patterns():
    """Analyze patterns in high-confidence questions to identify strategic approaches."""
    
    # Group questions by database strategy pattern
    specification_lookup = []
    application_search = []
    standards_cert = []
    material_construction = []
    comparative_analysis = []
    
    for q in HIGH_CONFIDENCE_QUESTIONS:
        strategy = q["database_strategy"].lower()
        
        if "product_code" in strategy and "specifications" in strategy:
            specification_lookup.append(q)
        elif "applications" in strategy:
            application_search.append(q)
        elif "standards" in strategy or "fda" in strategy or "dnv" in strategy:
            standards_cert.append(q)
        elif "construction_details" in strategy and ("material" in strategy or "rubber" in strategy):
            material_construction.append(q)
        elif "compare" in strategy or "difference" in strategy:
            comparative_analysis.append(q)
    
    print(f"\nHIGH-CONFIDENCE QUESTION PATTERN ANALYSIS:")
    print(f"=" * 60)
    print(f"Specification Lookup patterns: {len(specification_lookup)} questions")
    print(f"Application Search patterns: {len(application_search)} questions")
    print(f"Standards/Certification patterns: {len(standards_cert)} questions")  
    print(f"Material/Construction patterns: {len(material_construction)} questions")
    print(f"Comparative Analysis patterns: {len(comparative_analysis)} questions")
    
    return {
        "specification_lookup": specification_lookup,
        "application_search": application_search,
        "standards_cert": standards_cert,
        "material_construction": material_construction,
        "comparative_analysis": comparative_analysis
    }

if __name__ == "__main__":
    print_summary()
    print()
    analyze_high_confidence_patterns()