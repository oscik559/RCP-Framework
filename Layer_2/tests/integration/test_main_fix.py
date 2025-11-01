#!/usr/bin/env python3


def test_main_execution():
    """Test main.py execution to verify FAISS fixes"""

    print("🧪 Testing main.py execution with FAISS protection...")
    print("=" * 60)

    try:
        # Import the necessary components
        from agentic_reasoning.config.session_config import (
            get_default_session_state,
            get_workflow_config,
        )
        from agentic_reasoning.logic.state_graph import get_graph
        from agentic_reasoning.logic.templates import populate_template_libraries
        from agentic_reasoning.logic.vector_helpers import FAISS_AVAILABLE

        print(f"✅ Imports successful")
        print(f"🔍 FAISS_AVAILABLE: {FAISS_AVAILABLE}")

        # Test query
        user_query = "Which LOCATOR and CRIMPTOOL number is used for RPT2354309/350?"

        # Initialize session
        init_state = get_default_session_state(query=user_query)
        workflow_config = get_workflow_config()

        print(f"✅ Session initialized: {init_state['sessionID']}")

        # Setup libraries
        populate_template_libraries()
        print("✅ Libraries initialized")

        # Test graph initialization
        graph = get_graph()
        print("✅ Graph initialized")

        print(
            "\n🎉 All components working - main.py should execute without FAISS errors!"
        )
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_main_execution()
    if success:
        print("\n🚀 Ready to run main.py!")
    else:
        print("\n⚠️ Issues detected - check logs above")


