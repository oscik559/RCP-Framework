#!/usr/bin/env python3
"""
Strategy Testing Demo Script

This script demonstrates how to test individual strategies by configuring
the strategy_testing.py file to enable/disable specific strategies.

Usage Examples:
1. Test only "Simple lookup" strategy
2. Test only "Enhanced lookup and analysis" strategy
3. Test combinations of strategies
4. Compare performance between strategies
"""

import sys
import os

from agentic_reasoning.config.strategy_testing import STRATEGY_TEST_CONFIG, TESTING_MODE
from agentic_reasoning.config.debug_config import debug


def demo_single_strategy_testing():
    """Demo: Test only the Simple lookup strategy"""
    print("🧪 DEMO: Testing Single Strategy")
    print("=" * 50)

    # Example configuration for testing only Simple lookup
    config_example = {
        "Simple lookup": True,  # ✅ ENABLED
        "Enhanced lookup and analysis": False,  # ❌ DISABLED
        "Multi-document search": False,  # ❌ DISABLED
        "Cross-reference search": False,  # ❌ DISABLED
        "Product family search": False,  # ❌ DISABLED
        "Technical validation search": False,  # ❌ DISABLED
        "Advanced parallel search": False,  # ❌ DISABLED
    }

    print("To test only 'Simple lookup' strategy:")
    print("1. Edit project_saab/config/strategy_testing.py")
    print("2. Set TESTING_MODE = 'SINGLE_STRATEGY'")
    print("3. Update STRATEGY_TEST_CONFIG to:")
    for strategy, enabled in config_example.items():
        status = "✅ True " if enabled else "❌ False"
        print(f"   '{strategy}': {status}")
    print("4. Run: python main.py")
    print()


def demo_strategy_comparison():
    """Demo: Compare two strategies on the same query"""
    print("🔍 DEMO: Strategy Comparison Testing")
    print("=" * 50)

    print("To compare 'Simple lookup' vs 'Enhanced lookup and analysis':")
    print()
    print("Test 1: Simple lookup only")
    print("- Enable only 'Simple lookup' in strategy_testing.py")
    print("- Run the same query and note results")
    print()
    print("Test 2: Enhanced lookup only")
    print("- Enable only 'Enhanced lookup and analysis'")
    print("- Run the same query and compare:")
    print("  * Execution time")
    print("  * Answer quality")
    print("  * Number of functions executed")
    print("  * Success rate")
    print()


def demo_debugging_strategies():
    """Demo: Debug problematic strategies"""
    print("🐛 DEMO: Strategy Debugging")
    print("=" * 50)

    print("To debug a failing strategy:")
    print("1. Enable only the problematic strategy")
    print("2. Set debug level to detailed: debug.set_debug_level('detailed')")
    print("3. Watch function-by-function execution")
    print("4. Identify where it fails")
    print("5. Compare with working strategy execution")
    print()


def show_current_config():
    """Show current testing configuration"""
    print("📋 CURRENT CONFIGURATION")
    print("=" * 50)
    print(f"Testing Mode: {TESTING_MODE}")
    print("Strategy Configuration:")
    for strategy, enabled in STRATEGY_TEST_CONFIG.items():
        status = "✅ ENABLED " if enabled else "❌ DISABLED"
        print(f"  {status} {strategy}")
    print()


def main():
    """Main demo function"""
    print("🚀 SAAB Strategy Testing Framework Demo")
    print("=" * 60)
    print()

    show_current_config()
    demo_single_strategy_testing()
    demo_strategy_comparison()
    demo_debugging_strategies()

    print("💡 QUICK START:")
    print("1. Edit: project_saab/config/strategy_testing.py")
    print("2. Set TESTING_MODE = 'SINGLE_STRATEGY'")
    print("3. Enable only the strategy you want to test")
    print("4. Run: python main.py")
    print("5. Compare results with different strategies")
    print()


if __name__ == "__main__":
    main()


