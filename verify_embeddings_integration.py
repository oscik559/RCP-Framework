"""Quick verification that embeddings work with semantic search function."""
import sys
sys.path.insert(0, '.')

from Layer_2_Agentic.logic.embeddings import EmbeddingManager
from Layer_2_Agentic.logic.function_library import func_semantic_search

print('[TEST] Verifying embeddings database...')
mgr = EmbeddingManager()
if not mgr.load_model():
    print('[FAIL] Could not load model')
    sys.exit(1)

if not mgr.initialize_chroma():
    print('[FAIL] Could not initialize Chroma')
    sys.exit(1)

count = mgr.verify_embeddings()
if not count:
    print('[FAIL] Embeddings verification failed')
    sys.exit(1)

print('[OK] Embeddings database verified')
print()

# Test semantic search function
print('[TEST] Testing func_semantic_search with embeddings...')
result = func_semantic_search({'Input': 'high temperature hydraulic hose 350 bar'})
success, data = result

if not success:
    print(f'[FAIL] Search failed: {data}')
    sys.exit(1)

matches = data.get('Semantic Results', [])
print(f'[OK] Found {len(matches)} semantic matches')

for i, match in enumerate(matches[:2], 1):
    print(f'  {i}. {match.get("product_family")} (similarity: {match.get("similarity_score")})')

print()
print('[OK] All integration tests passed!')
