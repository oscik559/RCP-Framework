#!/usr/bin/env python3
"""Test the complete DIRECT_SPEC_LOOKUP strategy - Simplified"""

from Layer_2_Agentic.logic.function_library import func_extract_product_number, func_query_database
from Layer_2_Agentic.logic.llm_helpers import get_basic_llm
from langchain_core.prompts import ChatPromptTemplate
import json

print("=" * 70)
print("STRATEGY TEST: DIRECT_SPEC_LOOKUP (Simplified)")
print("=" * 70)
print()

# ========== STEP 1: Extract Product Number ==========
print("STEP 1: Extract Product Number")
print("-" * 70)
query = "What is the Slang ID for the product 4221-24-08?"
print(f"Query: {query}")
print()

params_extract = {"Input": query}
success_extract, result_extract = func_extract_product_number(params_extract)
product_code = result_extract.get("Keyword Output", "").strip()

print(f"✓ Extracted: {product_code}")
print()

# ========== STEP 2: Query Database ==========
print("STEP 2: Query Database (fetch product specs)")
print("-" * 70)

params_query = {
    "query_type": "custom",
    "custom_sql": f"SELECT product_code, specifications FROM products WHERE product_code = '{product_code}' LIMIT 1",
    "database_path": "database/harvested.db"
}

success_query, result_query = func_query_database(params_query)
print(f"✓ Query success: {success_query}")

if success_query and isinstance(result_query, dict):
    results = result_query.get('results', [])
    if results:
        product_data = results[0]
        specs_json = product_data.get('specifications', '{}')
        specs = json.loads(specs_json)
        
        print(f"✓ Product Code: {product_data.get('product_code')}")
        print(f"✓ All Specifications:")
        for key, value in specs.items():
            print(f"    {key}: {value}")
        print()
        
        # Extract the Slang ID
        slang_id = specs.get("Slang ID", "NOT FOUND")
        print(f"✓ TARGET ATTRIBUTE - Slang ID: {slang_id}")
        print()
        
        # ========== STEP 3: LLM Synthesis (Direct) ==========
        print("STEP 3: LLM Synthesis (direct)")
        print("-" * 70)
        
        # Build LLM prompt for synthesis
        specs_text = "\n".join([f"- {k}: {v}" for k, v in specs.items()])
        
        system_prompt = """You are a Hydroscand product database assistant.
Your task is to answer the user's question based on the product specifications provided.
Provide a clear, concise answer with the specific requested information."""

        user_prompt = f"""User Question: {query}

Product Information:
{specs_text}

Answer the question directly and concisely based on the product specifications above."""

        # Get LLM and create prompt template
        llm = get_basic_llm()
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt),
        ])
        
        chain = prompt | llm
        
        print("Calling LLM to synthesize answer...")
        print()
        
        response = chain.invoke({})
        final_answer = response.content if hasattr(response, 'content') else str(response)
        
        print("=" * 70)
        print("FINAL ANSWER:")
        print("=" * 70)
        print(final_answer)
        print()
        print("✅ STRATEGY COMPLETE!")
        print()
        print("=" * 70)
        print("VERIFICATION:")
        print("=" * 70)
        print(f"Expected attribute (Slang ID): {slang_id}")
        if slang_id.lower() in final_answer.lower():
            print("✅ Answer contains the correct Slang ID!")
        else:
            print("⚠️  Answer may need verification")
else:
    print(f"❌ Query failed")
