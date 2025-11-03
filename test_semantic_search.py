#!/usr/bin/env python3
"""
Test the new Semantic Search function implementation
"""

import sys
import os
sys.path.append('Layer_2-Agentic')

def test_semantic_search():
    """Test the semantic search function with a boiling water query."""
    
    try:
        from logic.function_library import func_semantic_search
        
        # Test parameters
        test_params = {
            'Input': 'What hoses can be used for boiling water?',
            'search_scope': 'both', 
            'similarity_threshold': 0.6,
            'max_results': 5
        }
        
        print('🧪 TESTING SEMANTIC SEARCH FUNCTION')
        print('=' * 60)
        print(f'Query: "{test_params["Input"]}"')
        print(f'Search Scope: {test_params["search_scope"]}')
        print(f'Similarity Threshold: {test_params["similarity_threshold"]}')
        print(f'Max Results: {test_params["max_results"]}')
        print()
        
        # Execute semantic search
        success, result = func_semantic_search(test_params)
        
        if success:
            print('✅ SEMANTIC SEARCH COMPLETED SUCCESSFULLY!')
            print('-' * 40)
            
            # Display results summary
            search_method = result.get('Search Method', 'unknown')
            total_matches = result.get('Total Matches', 0)
            
            print(f'🔍 Search Method Used: {search_method}')
            print(f'📊 Total Matches Found: {total_matches}')
            print()
            
            # Display semantic understanding
            understanding = result.get('Semantic Understanding', {})
            if understanding:
                print('🧠 SEMANTIC UNDERSTANDING:')
                print(f'   Primary Intent: {understanding.get("primary_intent", "unknown")}')
                
                app_context = understanding.get('application_context', {})
                if app_context:
                    print(f'   Application Context: {app_context.get("primary_use", "N/A")}')
                    print(f'   Environment: {app_context.get("environment", "N/A")}')
                
                search_concepts = understanding.get('search_concepts', [])
                if search_concepts:
                    print(f'   Search Concepts: {search_concepts[:5]}')
                print()
            
            # Display results
            semantic_results = result.get('Semantic Results', [])
            if semantic_results:
                print(f'📋 TOP SEMANTIC RESULTS ({len(semantic_results)} found):')
                print('-' * 40)
                
                for i, res in enumerate(semantic_results[:3], 1):
                    product_family = res.get('product_family', 'Unknown')
                    product_code = res.get('product_code', 'N/A')
                    similarity_score = res.get('similarity_score', 0)
                    match_reason = res.get('match_reason', 'No reason provided')
                    app_context = res.get('application_context', 'N/A')
                    tech_attrs = res.get('technical_attributes', {})
                    
                    print(f'{i}. PRODUCT: {product_family}')
                    if product_code != 'N/A':
                        print(f'   Code: {product_code}')
                    print(f'   Similarity Score: {similarity_score:.3f}')
                    print(f'   Match Reason: {match_reason}')
                    print(f'   Application Context: {app_context}')
                    
                    if tech_attrs:
                        print(f'   Technical Attributes:')
                        for attr, value in tech_attrs.items():
                            print(f'     - {attr}: {value}')
                    
                    source_info = res.get('source_info', {})
                    if source_info and source_info.get('filename'):
                        print(f'   Source: {source_info.get("filename", "Unknown")}')
                    
                    print()
            else:
                print('ℹ️ No semantic results found matching the criteria.')
                print('This could be due to:')
                print('   - High similarity threshold')
                print('   - Limited vector embeddings')
                print('   - Query not matching available content')
        
        else:
            print('❌ SEMANTIC SEARCH FAILED')
            print('-' * 30)
            print(f'Error: {result}')
            
    except ImportError as e:
        print(f'❌ Import Error: {e}')
        print('Make sure you are running from the correct directory')
        
    except Exception as e:
        print(f'💥 UNEXPECTED ERROR: {e}')
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_semantic_search()