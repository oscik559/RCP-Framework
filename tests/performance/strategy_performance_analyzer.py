#!/usr/bin/env python3
"""
Comprehensive Strategy Performance Analysis
==========================================

This script compares all available strategies acro                 # Parse results
            output = result.stdout
            success = "Goal OK: True" in output and "Strategy OK: True" in output
            
            # Alternative success criteria - if strategy completes all functions successfully
            if not success and "Strategy completed successfully" in output:
                success = True
                print("   ✅ Strategy completed successfully (alternative success criteria)")
            
            # Extract metrics
            function_count = output.count("🔹 EXECUTING:")
            parallel_groups = output.count("📊 Found parallel group:")# Extract metrics
            function_count = output.count("🔹 EXECUTING:")
            parallel_groups = output.count("📊 Found parallel group:")
            
            # Debug: Show what patterns we're finding
            print(f"   Debug: Found '🔹 EXECUTING:' {function_count} times")
            print(f"   Debug: Found '🚀 Starting:' {output.count('🚀 Starting:')} times")
            if function_count == 0:
                print("   Debug: Sample output (first 500 chars):")
                print(f"   {output[:500]}...")multiple metrics:
- Execution time
- Success rate  
- Function count
- Answer accuracy
- Resource usage

Tests each strategy with multiple queries from harvested.db to provide
statistical comparison data.
"""

import sqlite3
import subprocess
import time
import json
import os
from pathlib import Path
from typing import Dict, List, Any
import statistics

class StrategyPerformanceAnalyzer:
    """Analyzes and compares strategy performance across multiple dimensions."""
    
    def __init__(self):
        self.strategies = [
            "Simple lookup",
            "Enhanced lookup and analysis", 
            "Parallel multi-source search",
            # "Visual layout and analysis"  # Skip for now - requires images
        ]
        self.test_queries = []
        self.results = {}
        
    def load_test_queries(self, limit=6) -> List[Dict]:
        """Load diverse test queries from harvested.db"""
        db_path = "../database/harvested.db"
        
        if not os.path.exists(db_path):
            print(f"❌ Database not found: {db_path}")
            return []
        
        queries = []
        try:
            with sqlite3.connect(db_path) as conn:
                # Get successful queries from different categories
                cursor = conn.execute("""
                    SELECT test_query, category, execution_time_seconds 
                    FROM test_results 
                    WHERE status = 'SUCCESS' 
                    AND goal_satisfied = 1
                    AND strategy_satisfied = 1
                    AND test_query IS NOT NULL 
                    AND test_query != ''
                    AND LENGTH(test_query) < 200  -- Avoid overly complex queries
                    ORDER BY category, execution_time_seconds 
                    LIMIT ?
                """, (limit,))
                
                for row in cursor.fetchall():
                    queries.append({
                        'query': row[0],
                        'category': row[1] if row[1] else 'UNKNOWN',
                        'historical_time': row[2] if row[2] else 0.0
                    })
                    
        except Exception as e:
            print(f"❌ Error reading database: {e}")
            return []
        
        self.test_queries = queries
        return queries
    
    def update_strategy_config(self, strategy_name: str):
        """Enable only the specified strategy for testing"""
        config_file = "project_saab/config/strategy_testing.py"
        
        # Update strategy testing config
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple approach: replace the entire config block
            config_template = f'''# Available Strategies:
STRATEGY_TEST_CONFIG = {{
    "Simple lookup": {"True" if strategy_name == "Simple lookup" else "False"},
    "Enhanced lookup and analysis": {"True" if strategy_name == "Enhanced lookup and analysis" else "False"},
    "Visual layout and analysis": {"True" if strategy_name == "Visual layout and analysis" else "False"},
    "Parallel multi-source search": {"True" if strategy_name == "Parallel multi-source search" else "False"},
}}'''
            
            # Find and replace the config section
            start_marker = "# Available Strategies:"
            end_marker = "}"
            
            start_pos = content.find(start_marker)
            if start_pos != -1:
                end_pos = content.find(end_marker, start_pos) + 1
                new_content = content[:start_pos] + config_template + content[end_pos:]
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                    
        except Exception as e:
            print(f"❌ Error updating strategy config: {e}")
            return False
            
        return True
    
    def update_main_query(self, query: str) -> bool:
        """Update the query in main.py"""
        main_file = "main.py"
        
        try:
            with open(main_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find and replace the user_query line
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'user_query = ' in line and not line.strip().startswith('#'):
                    # Preserve the indentation of the original line
                    indentation = line[:len(line) - len(line.lstrip())]
                    lines[i] = f'{indentation}user_query = "{query}"'
                    break
            
            with open(main_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
                
            return True
            
        except Exception as e:
            print(f"❌ Error updating main.py: {e}")
            return False
    
    def run_strategy_test(self, strategy: str, query: Dict, test_num: int) -> Dict:
        """Run a single strategy test and capture results"""
        print(f"\n📊 Testing Strategy: {strategy}")
        print(f"📝 Query: {query['query'][:60]}...")
        print(f"📂 Category: {query['category']}")
        
        # Configure strategy and query
        if not self.update_strategy_config(strategy):
            return {'success': False, 'error': 'Failed to configure strategy'}
        
        if not self.update_main_query(query['query']):
            return {'success': False, 'error': 'Failed to update query'}
        
        # Run the test
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ['python', 'main.py'],
                capture_output=True,
                text=True,
                timeout=180,  # 3 minute timeout
                cwd="."
            )
            
            execution_time = time.time() - start_time
            
            # Parse results
            output = result.stdout
            success = "Goal OK: True" in output and "Strategy OK: True" in output
            
            # Extract metrics
            function_count = output.count("� EXECUTING:")
            parallel_groups = output.count("📊 Found parallel group:")
            final_answer = ""
            
            if "📦 Final Answer:" in output:
                answer_start = output.find("📦 Final Answer:") + len("📦 Final Answer:")
                answer_end = output.find("parallelExecutionMode:", answer_start)
                if answer_end != -1:
                    final_answer = output[answer_start:answer_end].strip()
            
            return {
                'success': success,
                'execution_time': execution_time,
                'function_count': function_count,
                'parallel_groups': parallel_groups,
                'final_answer': final_answer,
                'output_length': len(output),
                'query': query['query'],
                'category': query['category'],
                'historical_time': query.get('historical_time', 0),
                'error': result.stderr if result.stderr else None
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Timeout (>3 minutes)',
                'execution_time': time.time() - start_time,
                'query': query['query'],
                'category': query['category']
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time,
                'query': query['query'],
                'category': query['category']
            }
    
    def analyze_results(self) -> Dict:
        """Comprehensive analysis of strategy performance"""
        analysis = {
            'strategy_comparison': {},
            'overall_metrics': {},
            'recommendations': []
        }
        
        print(f"\n{'='*80}")
        print("📊 COMPREHENSIVE STRATEGY PERFORMANCE ANALYSIS")
        print('='*80)
        
        # Strategy-by-strategy analysis
        for strategy in self.strategies:
            if strategy not in self.results:
                continue
                
            results = self.results[strategy]
            successful_results = [r for r in results if r['success']]
            failed_results = [r for r in results if not r['success']]
            
            if successful_results:
                avg_time = statistics.mean([r['execution_time'] for r in successful_results])
                avg_functions = statistics.mean([r['function_count'] for r in successful_results])
                success_rate = len(successful_results) / len(results) * 100
                
                # Compare with historical times
                time_comparisons = []
                for r in successful_results:
                    if r.get('historical_time', 0) > 0:
                        ratio = r['execution_time'] / r['historical_time']
                        time_comparisons.append(ratio)
                
                avg_historical_ratio = statistics.mean(time_comparisons) if time_comparisons else None
                
                analysis['strategy_comparison'][strategy] = {
                    'success_rate': success_rate,
                    'avg_execution_time': avg_time,
                    'avg_function_count': avg_functions,
                    'total_tests': len(results),
                    'successful_tests': len(successful_results),
                    'failed_tests': len(failed_results),
                    'historical_time_ratio': avg_historical_ratio
                }
            else:
                analysis['strategy_comparison'][strategy] = {
                    'success_rate': 0,
                    'total_tests': len(results),
                    'successful_tests': 0,
                    'failed_tests': len(failed_results),
                    'error_summary': [r.get('error', 'Unknown') for r in failed_results]
                }
        
        # Print detailed comparison
        print(f"\n📋 STRATEGY PERFORMANCE COMPARISON")
        print("-" * 50)
        
        for strategy, metrics in analysis['strategy_comparison'].items():
            print(f"\n🔸 {strategy}:")
            print(f"   Success Rate: {metrics.get('success_rate', 0):.1f}%")
            if 'avg_execution_time' in metrics:
                print(f"   Avg Execution Time: {metrics['avg_execution_time']:.1f}s")
                print(f"   Avg Function Count: {metrics['avg_function_count']:.1f}")
                if metrics.get('historical_time_ratio'):
                    print(f"   vs Historical Time: {metrics['historical_time_ratio']:.2f}x")
            print(f"   Tests: {metrics['successful_tests']}/{metrics['total_tests']}")
        
        # Generate recommendations
        if analysis['strategy_comparison']:
            # Best success rate
            best_success = max(analysis['strategy_comparison'].items(), 
                             key=lambda x: x[1].get('success_rate', 0))
            
            # Fastest execution (among successful strategies)
            fastest_strategies = {k: v for k, v in analysis['strategy_comparison'].items() 
                                if v.get('avg_execution_time')}
            if fastest_strategies:
                fastest = min(fastest_strategies.items(), 
                            key=lambda x: x[1]['avg_execution_time'])
                
                analysis['recommendations'].extend([
                    f"🏆 Most Reliable: {best_success[0]} ({best_success[1]['success_rate']:.1f}% success)",
                    f"⚡ Fastest: {fastest[0]} ({fastest[1]['avg_execution_time']:.1f}s avg)",
                ])
        
        print(f"\n🎯 RECOMMENDATIONS")
        print("-" * 20)
        for rec in analysis['recommendations']:
            print(f"   {rec}")
        
        return analysis
    
    def run_comprehensive_analysis(self):
        """Run complete performance analysis across all strategies"""
        print("🚀 COMPREHENSIVE STRATEGY PERFORMANCE ANALYSIS")
        print("=" * 55)
        
        # Load test queries
        print("📊 Loading test queries from harvested.db...")
        queries = self.load_test_queries(limit=3)  # Use 3 queries for comprehensive testing
        
        if not queries:
            print("❌ No test queries found. Please check harvested.db.")
            return
        
        print(f"✅ Found {len(queries)} test queries")
        
        # Test each strategy
        for strategy in self.strategies:
            print(f"\n🔬 TESTING STRATEGY: {strategy}")
            print("=" * 60)
            
            strategy_results = []
            
            for i, query in enumerate(queries, 1):
                result = self.run_strategy_test(strategy, query, i)
                strategy_results.append(result)
                
                # Brief result summary
                status = "✅ PASS" if result['success'] else "❌ FAIL"
                time_str = f"{result['execution_time']:.1f}s"
                functions = result.get('function_count', 0)
                
                print(f"   {status} - {time_str} - {functions} functions - {result['category']}")
                
                # Small delay between tests
                time.sleep(1)
            
            self.results[strategy] = strategy_results
        
        # Analyze and compare results
        analysis = self.analyze_results()
        
        # Save detailed results
        output_file = 'tests/strategy_performance_analysis.json'
        full_results = {
            'strategies_tested': self.strategies,
            'test_queries': queries,
            'detailed_results': self.results,
            'analysis': analysis,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(output_file, 'w') as f:
            json.dump(full_results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {output_file}")
        
        return analysis

def main():
    """Main execution function"""
    analyzer = StrategyPerformanceAnalyzer()
    analyzer.run_comprehensive_analysis()

if __name__ == "__main__":
    main()


