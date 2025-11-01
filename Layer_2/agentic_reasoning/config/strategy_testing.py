# agentic_reasoning/config/strategy_testing.py
"""
Strategy testing configuration and control system for the agentic reasoning system.

Provides fine-grained control over which strategies are available during testing,
development, and production workflows. Supports isolated testing of individual
strategies, A/B testing scenarios, and performance comparison frameworks.

Key Features:
- Individual strategy enable/disable controls
- Multiple testing modes (all, single, disabled strategies)
- Strategy performance isolation for benchmarking
- Configuration backup and restore for testing frameworks
- Testing mode validation and reporting utilities

Testing Modes:
- ALL_ENABLED: Use all available strategies (normal production mode)
- SINGLE_STRATEGY: Use only strategies marked as enabled (testing mode)
- DISABLED_STRATEGIES: Use only disabled strategies (edge case testing)

Strategy Configuration:
- Simple lookup: Fast path for direct product queries
- Enhanced lookup: Comprehensive multi-step analysis with normalization
- Visual layout: Image processing and document layout analysis
- Parallel enhanced: Concurrent processing for performance optimization

Usage Patterns:
- Performance testing: Enable one strategy at a time for benchmarking
- A/B testing: Compare enabled vs disabled strategy performance
- Development: Disable unstable strategies during feature development
- Production: Use ALL_ENABLED mode for full capability

Integration with Testing Frameworks:
- Compatible with strategy comparison testing tools
- Supports automated test suite configuration
- Enables isolated strategy performance measurement
- Provides configuration state management for test reproducibility
"""

# ═══════════════════════════════════════════════════════════════════════
# STRATEGY TESTING CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

# Individual strategy control - set True to enable, False to disable
STRATEGY_TEST_CONFIG = {
    "SIMPLE LOOKUP": True,  # Fast path for direct queries
    "ENHANCED LOOKUP": True,  # Multi-step comprehensive analysis
    "VISUAL LAYOUT": False,  # Image processing (experimental)
    "PARALLEL ENHANCED LOOKUP": True,  # Concurrent processing optimization
}

# Testing execution modes
TESTING_MODE = "SINGLE_STRATEGY"  # Options: "ALL_ENABLED", "SINGLE_STRATEGY", "DISABLED_STRATEGIES"


def get_enabled_strategies():
    """
    Get list of enabled strategies based on current testing configuration.

    Returns strategies based on the selected testing mode:
    - ALL_ENABLED: All available strategies regardless of config
    - SINGLE_STRATEGY: Only strategies marked as True in config
    - DISABLED_STRATEGIES: Only strategies marked as False (for edge testing)

    Returns:
        List[str]: Strategy names that should be available for execution
    """
    if TESTING_MODE == "ALL_ENABLED":
        return list(STRATEGY_TEST_CONFIG.keys())
    elif TESTING_MODE == "SINGLE_STRATEGY":
        return [name for name, enabled in STRATEGY_TEST_CONFIG.items() if enabled]
    elif TESTING_MODE == "DISABLED_STRATEGIES":
        return [name for name, enabled in STRATEGY_TEST_CONFIG.items() if not enabled]
    else:
        return list(STRATEGY_TEST_CONFIG.keys())


def print_testing_status():
    """
    Print current testing configuration for debugging and verification.

    Displays the active testing mode, enabled strategies, and configuration
    summary for development and testing visibility.
    """
    enabled = get_enabled_strategies()
    print("🧪 Strategy Testing Configuration")
    print("=" * 40)
    print(f"Mode: {TESTING_MODE}")
    print(f"Enabled Strategies ({len(enabled)}):")
    for strategy in enabled:
        print(f"  ✅ {strategy}")

    if TESTING_MODE == "SINGLE_STRATEGY":
        disabled = [
            name for name, enabled in STRATEGY_TEST_CONFIG.items() if not enabled
        ]
        if disabled:
            print(f"Disabled Strategies ({len(disabled)}):")
            for strategy in disabled:
                print(f"  ❌ {strategy}")
    print("=" * 40)
