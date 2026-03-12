# Case Study Roadmap: Hydroscand Industrial Hose Catalog Extraction

## Purpose
This document outlines the structure and writing plan for Section 4 (or 5) of the manuscript: **Domain Application—Industrial Hydraulic Component Catalog Extraction**.

---

## 1. Strategic Positioning of the Case Study

### Role in the Paper
- **Demonstrate instantiation** of the generic framework in a concrete industrial domain
- **Validate architectural claims**: modularity, traceability, validation-centric design
- **Illustrate RCP utility**: show how policy tables and run-time instances manifest in practice
- **Expose domain-specific challenges**: Swedish-language catalogs, thread standards, hierarchical product taxonomies

### What This Case Study Is NOT
- Not a comprehensive empirical evaluation (that belongs in a separate Evaluation section)
- Not a system demo—focus on architectural alignment and design rationale

---

## 2. Proposed Section Structure

### 4. Domain Application: Industrial Hydraulic Component Catalog

#### 4.1 Domain Context and Extraction Challenges
- Industrial hydraulic hose catalogs (Hydroscand Produktbok)
- Document characteristics: multi-page PDFs, dense specification tables, Swedish technical terminology
- Domain complexity: thread standards (G, JIC, ORFS, NPTF, BSP), pressure ratings, temperature ranges, material compatibility
- Hierarchical product structure: Categories → Product Families → Products

#### 4.2 Three-Layer Architecture Instantiation
- **Layer 1 (Extraction)**: PDF → PNG → Table Detection → Product Extraction → Structured Database
- **Layer 2 (Agentic Reasoning)**: Goal → Strategy → Function pattern with LLM orchestration
- **Layer 3 (Application)**: Web UI and CLI interfaces for end-user queries

#### 4.3 Relational Control Plane Implementation
- Schema design: `harvested.db` (domain knowledge) + `agentic.db` (orchestration artifacts)
- Policy tables: strategy templates, function templates, validation rules
- Run-time tables: goal instances, strategy instances, agent invocations, parameter logs

#### 4.4 Strategy and Agent Library Instantiation
- Domain-specific strategies: product search, specification lookup, compatibility checking
- Agent functions: `func_search_products`, `func_get_product_details`, table filtering, unit normalization
- Declarative function registration and parameter contracts

#### 4.5 Vision-Language Model Integration for Table Extraction
- Use of Ollama + Qwen for visual table detection and cell extraction
- Pipeline: page rendering → table bounding box detection → structured cell extraction → database insertion
- Handling of merged cells, multi-row headers, unit columns

#### 4.6 Validation Gates and Quality Assurance
- Schema completeness checks
- Full-text search (FTS5) for Swedish-language queries
- Traceability from query response → strategy → agent → source table cell

#### 4.7 Observations and Lessons Learned
- Modularity benefits: adding new product families without code changes
- Challenges encountered: ambiguous table structures, OCR artifacts, thread notation variants
- Alignment with framework claims

---

## 3. Key Claims to Support

| Framework Claim | Case Study Evidence |
|-----------------|---------------------|
| Domain-agnostic control loop | Same six-stage loop applied to hydraulic catalogs |
| RCP provides traceability | All extractions logged with source page, bounding box, timestamps |
| Strategy templates enable reuse | Product search and spec lookup strategies defined declaratively |
| Agent modularity | Function library with uniform interface; new functions added without orchestration changes |
| Validation-centric design | Multi-level checks: extraction validation, search validation, response validation |

---

## 4. Figures and Tables to Include

1. **Figure**: Three-layer architecture diagram (Extraction → Reasoning → Application)
2. **Figure**: Database schema (simplified ERD showing Categories, Product Families, Products, Knowledge)
3. **Table**: Example strategy template instantiation
4. **Table**: Agent function registry excerpt
5. **Figure**: Extraction pipeline flowchart (PDF → PNG → Table → Products → DB)

---

## 5. Writing Guidelines

- Maintain passive voice for process descriptions
- Use present tense for architectural descriptions, past tense for implementation decisions
- Preserve Swedish terminology where domain-appropriate (e.g., "Produktbok")
- Cite framework sections (Section 3.x) when showing alignment
- Avoid implementation minutiae—focus on architectural mapping

---

## 6. Dependencies

- Finalize extraction pipeline documentation
- Confirm database schema stability
- Prepare simplified architecture diagrams
- Extract representative query examples for illustration
