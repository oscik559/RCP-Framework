#!/usr/bin/env python3
"""
Test script for product location queries.
Tests the new PRODUCT LOCATION strategy.
"""
import sys
import os

# Add Layer_2 to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Layer_2'))

from agentic_reasoning.config.session_config import get_default_session_state, get_workflow_config
from agentic_reasoning.logic.state_graph import get_graph

def test_location_query(question: str, verbose: bool = False):
    """Test a location query."""
    print(f"\n{'='*80}")
    print(f"QUESTION: {question}")
    print(f"{'='*80}\n")
    
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
        print(f"\n✅ Strategy: {strategy}")
        
        # Show answer
        print(f"\n💬 Answer: {answer}")
        
        if verbose:
            print(f"\n📋 Full Details:")
            print(f"   Goal: {goal}")
            print(f"   State keys: {list(final_state.keys())}")
        
        return {
            "success": True,
            "question": question,
            "strategy": strategy,
            "answer": answer,
            "goal": goal
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "question": question,
            "error": str(e)
        }

def main():
    """Run location query tests."""
    print("\n" + "="*80)
    print("PRODUCT LOCATION QUERY TEST")
    print("="*80)
    
    # Test queries
    test_questions = [
        "Where is the product 1071-00-16?",
        "What page is product 1071-00-16 on?",
        "Where can I find product 1023-00-06 in the catalogue?",
    ]
    
    results = []
    for question in test_questions:
        result = test_location_query(question)
        results.append({
            'question': question,
            'result': result
        })
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    success_count = sum(1 for r in results if r['result'] and r['result'].get('answer'))
    print(f"✅ Successful queries: {success_count}/{len(test_questions)}")
    print(f"❌ Failed queries: {len(test_questions) - success_count}/{len(test_questions)}")

if __name__ == "__main__":
    main()
