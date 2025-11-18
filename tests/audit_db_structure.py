#!/usr/bin/env python3
"""
Audit script: Database structure and semantic search readiness
"""

import sqlite3
import json
from pathlib import Path

def audit_harvested_db():
    """Analyze harvested.db structure and content"""
    db_path = Path("database/harvested.db")
    print("=" * 70)
    print("HARVESTED DATABASE ANALYSIS")
    print("=" * 70)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Get tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\n📊 Tables ({len(tables)}): {', '.join(tables)}\n")

    # Product families
    cursor.execute("SELECT COUNT(*) FROM product_families")
    family_count = cursor.fetchone()[0]
    print(f"👪 Product Families: {family_count}")

    cursor.execute("PRAGMA table_info(product_families)")
    columns = [(col[1], col[2]) for col in cursor.fetchall()]
    print(f"   Columns: {', '.join([f'{c[0]}({c[1]})' for c in columns])}")

    # Sample family
    cursor.execute("""
        SELECT id, name, description, applications, construction_details 
        FROM product_families 
        WHERE applications IS NOT NULL 
        LIMIT 1
    """)
    sample = cursor.fetchone()
    if sample:
        print(f"\n   Sample Family Data:")
        print(f"   - ID: {sample[0]}")
        print(f"   - Name: {sample[1]}")
        print(f"   - Description length: {len(sample[2]) if sample[2] else 0} chars")
        print(f"   - Applications: {sample[3][:150] if sample[3] else 'None'}...")
        if sample[4]:
            try:
                details = json.loads(sample[4])
                print(f"   - Construction fields: {list(details.keys())}")
            except Exception as e:
                print(f"   - Construction parse error: {e}")

    # Products
    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]
    print(f"\n📦 Products: {product_count}")

    cursor.execute("PRAGMA table_info(products)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"   Columns: {', '.join(columns)}")

    # Sample product
    cursor.execute("""
        SELECT product_code, family_id, specifications 
        FROM products 
        WHERE specifications IS NOT NULL 
        LIMIT 1
    """)
    sample = cursor.fetchone()
    if sample:
        print(f"\n   Sample Product Data:")
        print(f"   - Code: {sample[0]}")
        print(f"   - Family ID: {sample[1]}")
        if sample[2]:
            try:
                specs = json.loads(sample[2])
                print(f"   - Spec fields: {list(specs.keys())[:10]}")
                print(f"   - Sample values: {dict(list(specs.items())[:3])}")
            except Exception as e:
                print(f"   - Specs parse error: {e}")

    # FTS
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%fts%'")
    fts_tables = [row[0] for row in cursor.fetchall()]
    print(f"\n🔍 Full-Text Search: {fts_tables if fts_tables else '❌ Not configured'}")

    conn.close()


def audit_vector_index():
    """Analyze Chroma vector index"""
    print("\n" + "=" * 70)
    print("VECTOR INDEX (CHROMA) ANALYSIS")
    print("=" * 70)

    vector_dir = Path("vector_index")
    
    if not vector_dir.exists():
        print("\n❌ Vector index directory NOT found")
        return

    print(f"\n✅ Vector index directory exists: {vector_dir}")
    
    chroma_db = vector_dir / "chroma.sqlite3"
    if not chroma_db.exists():
        print(f"❌ Chroma DB not found at {chroma_db}")
        return
    
    print(f"✅ Chroma DB exists: {chroma_db.stat().st_size:,} bytes")

    try:
        conn = sqlite3.connect(str(chroma_db))
        cursor = conn.cursor()

        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\n   Chroma tables: {', '.join(tables)}")

        # Get row counts
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   - {table}: {count} rows")
            except:
                pass

        # Check embeddings table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%embedding%'")
        embedding_tables = [row[0] for row in cursor.fetchall()]
        if embedding_tables:
            print(f"\n   📊 Embedding tables found: {embedding_tables}")
        else:
            print(f"\n   ⚠️  No embedding tables found - may need initialization")

        conn.close()
        print("✅ Chroma DB verified")

    except Exception as e:
        print(f"❌ Error reading Chroma DB: {e}")


def audit_temp_db():
    """Check temp.db functionality for large dataset assembly"""
    print("\n" + "=" * 70)
    print("TEMPORARY DATABASE (ASSEMBLY) CAPABILITY")
    print("=" * 70)

    from Layer_2_Agentic.db.connection import get_temp_connection

    try:
        conn = get_temp_connection()
        cursor = conn.cursor()

        # Check if temp DB exists and is accessible
        cursor.execute("SELECT sqlite_version()")
        version = cursor.fetchone()[0]
        print(f"\n✅ Temp DB accessible - SQLite version: {version}")

        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"   Current tables: {tables if tables else 'Empty (new DB)'}")

        # Test assembly capability
        cursor.execute("""
            CREATE TEMPORARY TABLE test_assembly (
                product_id INTEGER,
                product_name TEXT,
                specs JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Temp table creation works")

        # Test batch insert
        test_data = [
            (i, f"Product {i}", json.dumps({"pressure": 25 + i, "temp": 100 - i}))
            for i in range(100)
        ]
        cursor.executemany(
            "INSERT INTO test_assembly (product_id, product_name, specs) VALUES (?, ?, ?)",
            test_data
        )
        print(f"✅ Batch insert works (tested with 100 rows)")

        # Test query
        cursor.execute("SELECT COUNT(*) FROM test_assembly")
        count = cursor.fetchone()[0]
        print(f"✅ Query works (counted {count} rows)")

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"❌ Temp DB error: {e}")


def audit_llm_context_limits():
    """Check LLM context window and estimate handling"""
    print("\n" + "=" * 70)
    print("LLM CONTEXT WINDOW ANALYSIS")
    print("=" * 70)

    try:
        from Layer_2_Agentic.config.config_loader import CONFIG
        from Layer_2_Agentic.logic.llm_helpers import get_basic_llm

        print(f"\n📋 LLM Configuration:")
        print(f"   Model: {CONFIG.get('llm_model', 'unknown')}")
        print(f"   API: {CONFIG.get('ollama_api_url', 'unknown')}")

        # Estimate context limits
        models_context = {
            "llama3.2": 8192,
            "llama2": 4096,
            "mistral": 8192,
            "neural-chat": 4096,
        }

        model_name = CONFIG.get('llm_model', 'llama3.2')
        context_tokens = models_context.get(model_name, 4096)

        print(f"\n📊 Estimated Context Window:")
        print(f"   Model: {model_name}")
        print(f"   Context tokens: {context_tokens:,}")
        print(f"   Rough character limit: {context_tokens * 4:,} chars (4 chars/token avg)")

        # Calculate safe limits
        system_prompt_chars = 500  # System prompt overhead
        user_question_chars = 200  # User question
        safe_data_chars = (context_tokens * 4) - system_prompt_chars - user_question_chars
        
        print(f"\n   Safe data character limit: {safe_data_chars:,} chars")
        print(f"   Safe product count (100 chars each): {safe_data_chars // 100} products")
        print(f"   Safe product count (500 chars each): {safe_data_chars // 500} products")

        print(f"\n⚠️  RECOMMENDATIONS:")
        print(f"   - Filter to max 15-20 products before LLM analysis")
        print(f"   - Use temp.db for assembly of large result sets (50+ products)")
        print(f"   - Implement progressive filtering to avoid context overflow")

    except Exception as e:
        print(f"⚠️  Cannot determine LLM config: {e}")


if __name__ == "__main__":
    audit_harvested_db()
    audit_vector_index()
    audit_temp_db()
    audit_llm_context_limits()
    print("\n" + "=" * 70)
    print("✅ AUDIT COMPLETE")
    print("=" * 70)
