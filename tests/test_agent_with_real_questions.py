"""
Test new strategies with actual Hydroscand product catalogue questions.

Uses real product codes and families from harvested.db to test the complete
agent workflow: Goal → Strategy → Functions → Answer
"""

import sys
import os

# Add Layer_2_Agentic to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Layer_2_Agentic'))

from agentic_reasoning.config.session_config import get_default_session_state, get_workflow_config
from agentic_reasoning.logic.graph import get_graph
from agentic_reasoning.logic.templates import populate_template_libraries

# Real Hydroscand test questions from Chapter 1 (Hydraulic Hoses)
TEST_QUESTIONS = [
    # Product Comparison Strategy
    {
        "question": "Compare the pressure rating and flexibility of 2SN and 4SP hydraulic hoses",
        "expected_strategy": "PRODUCT COMPARISON",
        "category": "comparison"
    },
    
    # Technical Calculation Strategy
    {
        "question": "What hose diameter do I need for a flow rate of 60 liters per minute at 4.5 m/s velocity?",
        "expected_strategy": "TECHNICAL CALCULATION",
        "category": "calculation"
    },
    
    {
        "question": "Convert 320 bar working pressure to PSI",
        "expected_strategy": "TECHNICAL CALCULATION",
        "category": "conversion"
    },
    
    # Standard Compliance Strategy
    {
        "question": "What are the specifications for SAE 100R2 hydraulic hose standard?",
        "expected_strategy": "STANDARD COMPLIANCE",
        "category": "standards"
    },
    
    {
        "question": "Does EN 853 2SN meet the same requirements as SAE 100R2?",
        "expected_strategy": "STANDARD COMPLIANCE",
        "category": "standards"
    },
    
    # Smart Recommendation Strategy
    {
        "question": "Recommend a hose for mobile hydraulics operating at 350 bar in cold weather (-20°C to +80°C)",
        "expected_strategy": "SMART RECOMMENDATION",
        "category": "recommendation"
    },
    
    # Specification Analysis Strategy
    {
        "question": "I have a 3/4 inch hose rated at 350 bar. Can it safely handle 5000 psi?",
        "expected_strategy": "SPECIFICATION ANALYSIS",
        "category": "analysis"
    },
    
    {
        "question": "Convert 19mm hose diameter to inches and tell me if it's suitable for 50 L/min flow",
        "expected_strategy": "SPECIFICATION ANALYSIS",
        "category": "analysis"
    },
    
    # Complex Multi-Step Questions
    {
        "question": "What's the best hose for a mobile crane hydraulic system with 60 L/min flow, 320 bar pressure, operating in -25°C to +90°C, with limited installation space?",
        "expected_strategy": "SMART RECOMMENDATION or SPECIFICATION ANALYSIS",
        "category": "complex"
    },
    
    {
        "question": "Compare the bend radius and pressure rating of 2SN vs 2SC vs 4SP hoses and recommend which is best for tight spaces",
        "expected_strategy": "PRODUCT COMPARISON",
        "category": "complex"
    },
]


def print_header(title):
    """Print formatted header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def run_query_through_agent(question: str, test_info: dict):
    """
    Run a query through the complete agent workflow.
    
    Tests: Goal Definition → Strategy Selection → Function Execution → Answer
    """
    print(f"\n{'─'*80}")
    print(f"QUESTION: {question}")
    print(f"Expected Strategy: {test_info['expected_strategy']}")
    print(f"Category: {test_info['category']}")
    print(f"{'─'*80}\n")
    
    try:
        # Initialize session
        init_state = get_default_session_state(query=question)
        workflow_config = get_workflow_config()
        
        # Get the workflow graph
        graph = get_graph()
        
        # Execute workflow
        print("🤖 Running agent workflow...")
        print("   Step 1: Defining goal...")
        
        final_state = graph.invoke(init_state, config=workflow_config)
        
        # Extract results
        session_id = final_state.get('sessionID')
        current_goal = final_state.get('currentGoalText', 'No goal defined')
        selected_strategy = final_state.get('currentStrategyName', 'No strategy selected')
        answer = final_state.get('answer', 'No answer generated')
        
        # Display results
        print(f"\n✅ Workflow completed!")
        print(f"\n📋 RESULTS:")
        print(f"   Session ID: {session_id}")
        print(f"   Goal: {current_goal[:100]}...")
        print(f"   Strategy Selected: {selected_strategy}")
        print(f"   Expected Strategy: {test_info['expected_strategy']}")
        
        # Check if correct strategy was selected
        strategy_match = selected_strategy == test_info['expected_strategy']
        strategy_status = "✅ MATCH" if strategy_match else "⚠️  DIFFERENT"
        print(f"   Strategy Match: {strategy_status}")
        
        print(f"\n💬 ANSWER:")
        # Print first 500 characters of answer
        answer_preview = answer[:500] + "..." if len(answer) > 500 else answer
        print(f"   {answer_preview}")
        
        return {
            "success": True,
            "question": question,
            "goal": current_goal,
            "strategy": selected_strategy,
            "expected_strategy": test_info['expected_strategy'],
            "strategy_match": strategy_match,
            "answer": answer,
            "category": test_info['category']
        }
        
    except Exception as e:
        print(f"\n❌ Error running query: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "question": question,
            "error": str(e),
            "category": test_info['category']
        }


def main():
    """Run all test questions through the agent."""
    print_header("TESTING NEW STRATEGIES WITH REAL HYDROSCAND QUESTIONS")
    
    print(f"Testing {len(TEST_QUESTIONS)} questions from Chapter 1 (Hydraulic Hoses)")
    print("\nQuestions cover:")
    print("  • Product comparisons (2SN, 4SP, 2SC hoses)")
    print("  • Technical calculations (diameter, flow, pressure)")
    print("  • Unit conversions (bar ↔ PSI, inch ↔ mm)")
    print("  • Standards compliance (SAE 100R2, EN 853)")
    print("  • Smart recommendations (application-specific)")
    print("  • Specification analysis (safety checks)")
    print("  • Complex multi-step queries")
    
    # Initialize template libraries
    print("\n📚 Initializing template libraries...")
    populate_template_libraries()
    print("✅ Templates loaded: 10 strategies, 27 functions")
    
    # Run tests
    results = []
    
    for i, test_case in enumerate(TEST_QUESTIONS, 1):
        print(f"\n\n{'='*80}")
        print(f"TEST {i}/{len(TEST_QUESTIONS)}")
        print(f"{'='*80}")
        
        result = run_query_through_agent(test_case["question"], test_case)
        results.append(result)
        
        # Brief pause between tests
        print("\n⏸️  Pausing 2 seconds before next test...")
        import time
        time.sleep(2)
    
    # Summary
    print_header("TEST SUMMARY")
    
    successful = sum(1 for r in results if r.get("success", False))
    strategy_matches = sum(1 for r in results if r.get("strategy_match", False))
    
    print(f"Tests Run: {len(results)}")
    print(f"Successful: {successful}/{len(results)}")
    print(f"Strategy Matches: {strategy_matches}/{successful}")
    
    # Breakdown by category
    print(f"\n📊 Results by Category:")
    categories = {}
    for r in results:
        cat = r.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"total": 0, "success": 0, "match": 0}
        categories[cat]["total"] += 1
        if r.get("success"):
            categories[cat]["success"] += 1
        if r.get("strategy_match"):
            categories[cat]["match"] += 1
    
    for cat, stats in categories.items():
        print(f"   {cat:15s}: {stats['success']}/{stats['total']} successful, {stats['match']} strategy matches")
    
    # Detailed results
    print(f"\n📋 Detailed Results:")
    for i, r in enumerate(results, 1):
        status = "✅" if r.get("success") else "❌"
        strategy_status = "✅" if r.get("strategy_match") else "⚠️ "
        print(f"\n{i}. {status} {r.get('question', 'Unknown')[:60]}...")
        if r.get("success"):
            print(f"   Strategy: {strategy_status} {r.get('strategy', 'N/A')} (expected: {r.get('expected_strategy', 'N/A')})")
        else:
            print(f"   Error: {r.get('error', 'Unknown error')}")
    
    # Final status
    print(f"\n{'='*80}")
    if successful == len(results) and strategy_matches == successful:
        print("🎉 ALL TESTS PASSED! All strategies working correctly!")
    elif successful == len(results):
        print(f"✅ All queries completed, but {successful - strategy_matches} used different strategies")
    else:
        print(f"⚠️  {len(results) - successful} tests failed")
    print(f"{'='*80}\n")
    
    return 0 if successful == len(results) else 1


if __name__ == "__main__":
    exit(main())
