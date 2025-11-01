"""
Test FAQ - Real Questions from Hydroscand Company FAQ

This test script contains curated questions from the actual Hydroscand FAQ
that are relevant to Chapter 1 (Hydraulic Hoses) of the product catalogue.

These are real-world questions that customers ask, testing:
- Product specifications lookup
- Pressure and temperature ratings
- Standards compliance (SAE, EN, ISO)
- Product comparisons (2SN vs 2SC, 42 vs 47 series)
- Technical calculations (flow rate, hose sizing)
- Material compatibility and applications
- Product selection and recommendations
"""

import sys
import os

# Add Layer_2 to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Layer_2'))

from agentic_reasoning.config.session_config import get_default_session_state, get_workflow_config
from agentic_reasoning.logic.graph import get_graph
from agentic_reasoning.logic.templates import populate_template_libraries

# ============================================================================
# CURATED TEST QUESTIONS FROM CHAPTER 1 (HYDRAULIC HOSES)
# ============================================================================
# These are actual FAQ questions from test_questions_en.xlsx

FAQ_CHAPTER1_QUESTIONS = [
    # ========== PRODUCT SPECIFICATIONS ==========
    {
        "id": 59,
        "question": "What is the maximum temperature for hose 1071-00-16?",
        "category": "specification",
        "expected_strategy": "SIMPLE LOOKUP or SPECIFICATION ANALYSIS",
        "difficulty": "easy"
    },
    {
        "id": 49,
        "question": "What maximum working pressure is 427012062 rated for?",
        "category": "specification", 
        "expected_strategy": "SIMPLE LOOKUP",
        "difficulty": "easy"
    },
    {
        "id": 61,
        "question": "What is the working pressure of a 4201-16-16?",
        "category": "specification",
        "expected_strategy": "SIMPLE LOOKUP",
        "difficulty": "easy"
    },
    {
        "id": 62,
        "question": "What is the working pressure for 4253-24-24?",
        "category": "specification",
        "expected_strategy": "SIMPLE LOOKUP",
        "difficulty": "easy"
    },
    {
        "id": 63,
        "question": "What is the working pressure for 4743-20-20?",
        "category": "specification",
        "expected_strategy": "SIMPLE LOOKUP",
        "difficulty": "easy"
    },
    
    # ========== PRODUCT COMPARISONS ==========
    {
        "id": 30,
        "question": "What is the difference between a 2SN and 2SC hose?",
        "category": "comparison",
        "expected_strategy": "PRODUCT COMPARISON",
        "difficulty": "medium"
    },
    {
        "id": 4,
        "question": "What is the difference between product A and B?",
        "category": "comparison",
        "expected_strategy": "PRODUCT COMPARISON",
        "difficulty": "easy",
        "note": "Generic question - would need specific products"
    },
    {
        "id": 70,
        "question": "What is the difference between the 42 series and the 47 series?",
        "category": "comparison",
        "expected_strategy": "PRODUCT COMPARISON",
        "difficulty": "medium"
    },
    
    # ========== TECHNICAL CALCULATIONS ==========
    {
        "id": 43,
        "question": "The flow is 150 liters per minute, what hose dimension should I choose for pressure?",
        "category": "calculation",
        "expected_strategy": "TECHNICAL CALCULATION",
        "difficulty": "medium"
    },
    {
        "id": 44,
        "question": "The flow is 20 liters per minute, what hose dimension should I choose for suction/return?",
        "category": "calculation",
        "expected_strategy": "TECHNICAL CALCULATION",
        "difficulty": "medium"
    },
    {
        "id": 45,
        "question": "The flow is 100 liters per minute and I can have a maximum pressure drop of 200 millibars, what hose dimension?",
        "category": "calculation",
        "expected_strategy": "TECHNICAL CALCULATION",
        "difficulty": "hard"
    },
    {
        "id": 34,
        "question": "How many millimeters is 1/8 inch?",
        "category": "conversion",
        "expected_strategy": "TECHNICAL CALCULATION",
        "difficulty": "easy"
    },
    
    # ========== STANDARDS COMPLIANCE ==========
    {
        "id": 13,
        "question": "Do you have hoses that meet the EN 857 standard?",
        "category": "standards",
        "expected_strategy": "STANDARD COMPLIANCE",
        "difficulty": "medium"
    },
    {
        "id": 68,
        "question": "What standards are there for hydraulic hose?",
        "category": "standards",
        "expected_strategy": "STANDARD COMPLIANCE",
        "difficulty": "medium"
    },
    {
        "id": 67,
        "question": "What is ISO bar?",
        "category": "standards",
        "expected_strategy": "STANDARD COMPLIANCE",
        "difficulty": "easy"
    },
    
    # ========== PRESSURE RATINGS ==========
    {
        "id": 31,
        "question": "Which hydraulic hoses are rated for more than 300 bar working pressure?",
        "category": "search",
        "expected_strategy": "SIMPLE LOOKUP or SMART RECOMMENDATION",
        "difficulty": "medium"
    },
    {
        "id": 71,
        "question": "Which hose should I use if I have 380 bar in the machine?",
        "category": "recommendation",
        "expected_strategy": "SMART RECOMMENDATION",
        "difficulty": "medium"
    },
    {
        "id": 16,
        "question": "What is the maximum working pressure for this hose at 100 °C?",
        "category": "specification",
        "expected_strategy": "SPECIFICATION ANALYSIS",
        "difficulty": "medium",
        "note": "Temperature-dependent pressure rating"
    },
    
    # ========== APPLICATION-SPECIFIC ==========
    {
        "id": 1,
        "question": "What hoses can be used for boiling water?",
        "category": "application",
        "expected_strategy": "SMART RECOMMENDATION",
        "difficulty": "medium"
    },
    {
        "id": 17,
        "question": "What hoses can be used for chemicals?",
        "category": "application",
        "expected_strategy": "SMART RECOMMENDATION",
        "difficulty": "medium"
    },
    {
        "id": 41,
        "question": "Hose for alkaline degreasing?",
        "category": "application",
        "expected_strategy": "SMART RECOMMENDATION",
        "difficulty": "medium"
    },
    {
        "id": 69,
        "question": "Can I use environmental oil in 1105-63?",
        "category": "compatibility",
        "expected_strategy": "SPECIFICATION ANALYSIS",
        "difficulty": "medium"
    },
    
    # ========== PRODUCT SELECTION ==========
    {
        "id": 3,
        "question": "Which hydraulic hose and sleeve should I get for a particular excavator?",
        "category": "recommendation",
        "expected_strategy": "SMART RECOMMENDATION",
        "difficulty": "hard"
    },
    {
        "id": 2,
        "question": "Which sleeve should I get for hose X?",
        "category": "recommendation",
        "expected_strategy": "SIMPLE LOOKUP or GET RELATED ITEMS",
        "difficulty": "easy"
    },
    {
        "id": 15,
        "question": "Do you have a product that can withstand both high pressure and vibrations?",
        "category": "recommendation",
        "expected_strategy": "SMART RECOMMENDATION",
        "difficulty": "hard"
    },
    
    # ========== CERTIFICATIONS & APPROVALS ==========
    {
        "id": 7,
        "question": "Which products are approved for food use?",
        "category": "certification",
        "expected_strategy": "SIMPLE LOOKUP",
        "difficulty": "medium"
    },
    {
        "id": 77,
        "question": "Which hoses are FDA approved for food use?",
        "category": "certification",
        "expected_strategy": "SIMPLE LOOKUP",
        "difficulty": "medium"
    },
    {
        "id": 76,
        "question": "Which hoses are DNV classified?",
        "category": "certification",
        "expected_strategy": "SIMPLE LOOKUP",
        "difficulty": "medium"
    },
    
    # ========== SPECIAL FEATURES ==========
    {
        "id": 74,
        "question": "Is there a hose with a smooth outer casing?",
        "category": "feature",
        "expected_strategy": "SIMPLE LOOKUP or DISCOVER ITEMS",
        "difficulty": "medium"
    },
    {
        "id": 18,
        "question": "Natural rubber hoses?",
        "category": "material",
        "expected_strategy": "SIMPLE LOOKUP",
        "difficulty": "easy"
    },
    
    # ========== PRODUCT LOCATION ==========
    {
        "id": 28,
        "question": "Where is the product 1452-00-12 or 1452-10-12?",
        "category": "location",
        "expected_strategy": "PRODUCT LOCATION",
        "difficulty": "easy",
        "note": "Tests page number and catalogue location lookup"
    },
    {
        "id": 64,
        "question": "Where can I find assembly instructions for Hydroscand cutting ring couplings?",
        "category": "location",
        "expected_strategy": "PRODUCT LOCATION or SIMPLE LOOKUP",
        "difficulty": "medium",
        "note": "Tests document/instruction location"
    },
]


def print_header(title):
    """Print formatted header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def run_faq_question(test_case: dict, verbose: bool = False):
    """
    Run a single FAQ question through the agent.
    
    Args:
        test_case: Dict with question, category, expected_strategy, etc.
        verbose: If True, show detailed workflow output
        
    Returns:
        Dict with test results
    """
    question = test_case["question"]
    
    if not verbose:
        print(f"\n{'─'*80}")
        print(f"Q{test_case['id']}: {question}")
        print(f"Category: {test_case['category']} | Difficulty: {test_case['difficulty']}")
        print(f"{'─'*80}")
    
    try:
        # Initialize session
        init_state = get_default_session_state(query=question)
        workflow_config = get_workflow_config()
        
        # Get workflow graph
        graph = get_graph()
        
        if verbose:
            print(f"\n🤖 Processing: {question}")
        
        # Execute workflow
        final_state = graph.invoke(init_state, config=workflow_config)
        
        # Extract results
        strategy = final_state.get('currentStrategyName', 'Unknown')
        answer = final_state.get('answer', 'No answer generated')
        goal = final_state.get('currentGoalText', 'No goal')
        
        # Display results
        if not verbose:
            print(f"\n✅ Strategy: {strategy}")
            print(f"   Expected: {test_case['expected_strategy']}")
            
            # Show answer preview (first 200 chars)
            answer_preview = answer[:200] + "..." if len(answer) > 200 else answer
            print(f"\n💬 Answer: {answer_preview}")
        else:
            print(f"\n📋 Results:")
            print(f"   Goal: {goal}")
            print(f"   Strategy: {strategy}")
            print(f"   Answer: {answer}")
        
        return {
            "success": True,
            "id": test_case["id"],
            "question": question,
            "category": test_case["category"],
            "difficulty": test_case["difficulty"],
            "strategy": strategy,
            "expected_strategy": test_case["expected_strategy"],
            "answer": answer,
            "goal": goal
        }
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        if verbose:
            traceback.print_exc()
        
        return {
            "success": False,
            "id": test_case["id"],
            "question": question,
            "category": test_case["category"],
            "error": str(e)
        }


def main():
    """Run FAQ tests."""
    print_header("HYDROSCAND FAQ TEST - CHAPTER 1 (HYDRAULIC HOSES)")
    
    print(f"Testing {len(FAQ_CHAPTER1_QUESTIONS)} real customer questions")
    print("\nQuestion Categories:")
    categories = {}
    for q in FAQ_CHAPTER1_QUESTIONS:
        cat = q["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in sorted(categories.items()):
        print(f"  • {cat:20s}: {count} questions")
    
    # Initialize templates
    print("\n📚 Initializing template libraries...")
    populate_template_libraries()
    print("✅ Templates loaded")
    
    # Ask user which questions to test
    print("\n" + "="*80)
    print("TEST OPTIONS:")
    print("="*80)
    print("1. Test ALL questions (30 questions)")
    print("2. Test by difficulty:")
    print("   - Easy questions (10)")
    print("   - Medium questions (15)")
    print("   - Hard questions (5)")
    print("3. Test by category")
    print("4. Test specific question IDs")
    print("5. Quick test (5 representative questions)")
    
    choice = input("\nEnter choice (1-5) [default: 5]: ").strip() or "5"
    
    # Select questions based on choice
    if choice == "1":
        selected = FAQ_CHAPTER1_QUESTIONS
    elif choice == "2":
        diff = input("Enter difficulty (easy/medium/hard): ").strip().lower()
        selected = [q for q in FAQ_CHAPTER1_QUESTIONS if q["difficulty"] == diff]
    elif choice == "3":
        cat = input(f"Enter category {list(categories.keys())}: ").strip()
        selected = [q for q in FAQ_CHAPTER1_QUESTIONS if q["category"] == cat]
    elif choice == "4":
        ids = input("Enter question IDs (comma-separated): ").strip()
        ids = [int(x.strip()) for x in ids.split(",")]
        selected = [q for q in FAQ_CHAPTER1_QUESTIONS if q["id"] in ids]
    else:  # Quick test
        selected = [
            FAQ_CHAPTER1_QUESTIONS[0],   # Temperature spec
            FAQ_CHAPTER1_QUESTIONS[5],   # 2SN vs 2SC comparison
            FAQ_CHAPTER1_QUESTIONS[8],   # Flow calculation
            FAQ_CHAPTER1_QUESTIONS[12],  # Standards
            FAQ_CHAPTER1_QUESTIONS[17],  # Pressure rating recommendation
        ]
    
    verbose = input("\nVerbose output? (y/n) [default: n]: ").strip().lower() == 'y'
    
    print(f"\n{'='*80}")
    print(f"Running {len(selected)} questions...")
    print(f"{'='*80}")
    
    # Run tests
    results = []
    for i, test_case in enumerate(selected, 1):
        print(f"\n\n{'='*80}")
        print(f"TEST {i}/{len(selected)}")
        print(f"{'='*80}")
        
        result = run_faq_question(test_case, verbose=verbose)
        results.append(result)
        
        # Pause between tests
        if i < len(selected):
            import time
            time.sleep(1)
    
    # Summary
    print_header("TEST SUMMARY")
    
    successful = sum(1 for r in results if r.get("success", False))
    total = len(results)
    
    print(f"Tests Run: {total}")
    print(f"Successful: {successful}/{total} ({successful/total*100:.1f}%)")
    
    # Results by category
    print(f"\n📊 Results by Category:")
    cat_stats = {}
    for r in results:
        cat = r.get("category", "unknown")
        if cat not in cat_stats:
            cat_stats[cat] = {"total": 0, "success": 0}
        cat_stats[cat]["total"] += 1
        if r.get("success"):
            cat_stats[cat]["success"] += 1
    
    for cat, stats in sorted(cat_stats.items()):
        pct = stats["success"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"   {cat:20s}: {stats['success']}/{stats['total']} ({pct:.0f}%)")
    
    # Results by difficulty
    print(f"\n📊 Results by Difficulty:")
    diff_stats = {}
    for r in results:
        diff = r.get("difficulty", "unknown")
        if diff not in diff_stats:
            diff_stats[diff] = {"total": 0, "success": 0}
        diff_stats[diff]["total"] += 1
        if r.get("success"):
            diff_stats[diff]["success"] += 1
    
    for diff in ["easy", "medium", "hard"]:
        if diff in diff_stats:
            stats = diff_stats[diff]
            pct = stats["success"] / stats["total"] * 100 if stats["total"] > 0 else 0
            print(f"   {diff:20s}: {stats['success']}/{stats['total']} ({pct:.0f}%)")
    
    # Detailed results
    print(f"\n📋 Detailed Results:")
    for i, r in enumerate(results, 1):
        status = "✅" if r.get("success") else "❌"
        print(f"\n{i}. {status} Q{r['id']}: {r['question'][:60]}...")
        if r.get("success"):
            print(f"   Strategy: {r.get('strategy', 'N/A')}")
            print(f"   Expected: {r.get('expected_strategy', 'N/A')}")
        else:
            print(f"   Error: {r.get('error', 'Unknown')}")
    
    # Final status
    print(f"\n{'='*80}")
    if successful == total:
        print("🎉 ALL FAQ TESTS PASSED!")
        print("The system successfully handled all real customer questions!")
    else:
        print(f"⚠️  {total - successful} questions failed")
        print("Review the errors above for improvements needed")
    print(f"{'='*80}\n")
    
    return 0 if successful == total else 1


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
