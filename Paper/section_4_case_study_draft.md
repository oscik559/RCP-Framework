# 4. Domain Application: Industrial Hydraulic Component Catalog Extraction

This section presents an instantiation of the proposed framework within the domain of industrial hydraulic component catalogs. The application targets the Hydroscand Produktbok—a comprehensive Swedish-language catalog of high-pressure hoses, couplings, and associated fittings. This domain exemplifies the challenges motivating the framework: dense tabular specifications, hierarchical product taxonomies, domain-specific standards, and the need for precise, traceable retrieval.

---

## 4.1 Domain Context and Extraction Challenges

Industrial hydraulic catalogs present a demanding extraction environment. The Hydroscand Produktbok comprises multi-page PDF documents containing:

- **Dense specification tables**: Product dimensions, pressure ratings, temperature ranges, and material compositions are encoded in compact tabular formats with merged cells and multi-row headers.
- **Hierarchical product structure**: Products are organized into categories (e.g., high-pressure hoses, thermoplastic hoses), which contain product families, each comprising individual product variants with distinct specifications.
- **Domain-specific standards**: Coupling specifications reference thread standards (G, JIC, ORFS, NPTF, BSP) with precise dimensional tolerances. Accurate extraction requires preservation of these notations without normalization artifacts.
- **Swedish technical terminology**: All catalog content is presented in Swedish, necessitating language-aware processing for both extraction and subsequent retrieval.

Traditional RAG approaches struggle with such documents. Text-based chunking disrupts table semantics; OCR pipelines introduce artifacts in technical notations; and generic retrievers lack the domain grounding required for specification-level queries. The proposed framework addresses these limitations through structured extraction, a relational control plane, and validation-gated agent orchestration.

---

## 4.2 Three-Layer Architecture Instantiation

The implementation realizes the framework through a three-layer architecture, each layer addressing a distinct concern:

### Layer 1: Extraction Pipeline

The extraction layer transforms raw PDF catalogs into a structured relational database. The pipeline proceeds through four stages:

1. **PDF to PNG conversion**: Each catalog page is rendered as a high-resolution image, preserving visual layout for subsequent table detection.
2. **Table detection**: A Vision-Language Model (VLM)—specifically Qwen via Ollama—identifies table regions and outputs bounding box coordinates.
3. **Cell extraction**: Detected tables are processed to extract individual cell contents, reconstruct row–column structure, and identify header rows.
4. **Database insertion**: Extracted products are inserted into a normalized SQLite database (`harvested.db`) with full-text search (FTS5) enabled for Swedish-language queries.

This layer operates independently of the reasoning layer, producing a stable domain knowledge base that can be queried by multiple downstream strategies.

### Layer 2: Agentic Reasoning

The reasoning layer implements the six-stage control loop described in Section 3. User queries are normalized into goal objects specifying required evidence (e.g., product specifications, compatibility constraints). A strategy is selected from the strategy library, and eligible agents are invoked in sequence. Each agent invocation is logged to the orchestration database (`agentic.db`), and validation gates assess progress before advancing.

The layer employs LangGraph for workflow orchestration and LangChain for LLM integration, with all orchestration artifacts persisted in the Relational Control Plane.

### Layer 3: Application Interface

The application layer provides two access modalities:

- **Command-line interface (CLI)**: For batch queries and scripted workflows.
- **Web interface**: A Flask-based UI enabling interactive queries with progress tracking and result visualization.

Both interfaces invoke the reasoning layer through a unified API, ensuring consistent behavior and traceability.

---

## 4.3 Relational Control Plane Implementation

The RCP is realized through two coordinated databases:

### Domain Knowledge Database (`harvested.db`)

This database stores extracted catalog content in a normalized schema:

- **Categories**: Top-level product groupings (e.g., "High-Pressure Hoses").
- **Product Families**: Named collections within categories, with descriptive metadata.
- **Products**: Individual items with JSON-encoded specifications (dimensions, ratings, materials), source page references, and bounding box coordinates for traceability.
- **Knowledge**: Supplementary textual content extracted from non-tabular regions.

Full-text search is enabled via FTS5 virtual tables, supporting Swedish-language queries across product names, descriptions, and specifications.

### Orchestration Database (`agentic.db`)

This database implements the RCP schema described in Section 3.1:

**Design-time tables** define:
- Strategy templates with target variables and sufficiency conditions
- Agent function templates with input–output contracts
- Validation rule definitions

**Run-time tables** record:
- Goal instances with timestamps and completion status
- Strategy instances linked to parent goals
- Agent invocations with serialized parameters and outputs
- Validation results and diagnostic messages

This separation enables deterministic replay, audit queries, and lineage tracing from any response artifact back to source extraction.

---

## 4.4 Strategy and Agent Library Instantiation

### Strategy Templates

The implementation includes domain-specific strategy templates:

| Strategy | Description | Sufficiency Condition |
|----------|-------------|----------------------|
| `product_search` | Retrieve products matching keyword or attribute criteria | At least one matching product with valid specifications |
| `spec_lookup` | Extract specific attributes from identified products | Target attribute present with unit normalization |
| `compatibility_check` | Verify thread or coupling compatibility between components | Matching thread standards confirmed |
| `family_summary` | Aggregate specifications across a product family | All family members retrieved with consistent schema |

Each strategy specifies eligible agents, fallback policies (e.g., broaden search scope), and validation requirements.

### Agent Function Library

Agents are implemented as stateless functions with declared interfaces:

```
func_search_products(keywords, filters, limit) → {products[], count}
func_get_product_details(product_id) → {specifications{}, source_page}
func_filter_by_attribute(products[], attribute, constraint) → {filtered[]}
func_normalize_units(value, source_unit, target_unit) → {normalized_value}
func_get_family_products(family_id) → {products[], family_metadata}
```

All functions are registered in a central function library with metadata enabling dynamic selection based on strategy requirements. New functions can be added by inserting registry entries—no orchestration code modification is required.

---

## 4.5 Vision-Language Model Integration

Table extraction employs a VLM pipeline to address the limitations of text-based PDF parsing:

1. **Page rendering**: PDF pages are converted to PNG at 300 DPI to preserve fine tabular details.
2. **Table region detection**: The VLM receives page images with structured prompts requesting bounding box coordinates for detected tables.
3. **Cell-level extraction**: Identified table regions are processed to extract cell contents, with attention to merged cells and hierarchical headers.
4. **Structured output**: Extracted data is formatted as JSON with row–column indices, enabling direct database insertion.

This approach preserves spatial relationships that text extraction destroys, maintaining the semantic integrity of specification tables.

---

## 4.6 Validation Gates and Quality Assurance

The implementation enforces validation at multiple levels:

### Extraction Validation
- Schema completeness: All required fields (product ID, name, specifications) must be present.
- Bounding box plausibility: Detected regions must fall within page dimensions.
- Duplicate detection: Products with matching identifiers trigger merge-or-reject decisions.

### Query Validation
- Parameter type checking: Agent inputs are validated against declared contracts.
- Result non-emptiness: Strategies require minimum evidence thresholds before proceeding.

### Response Validation
- Citation anchoring: All responses include source page and table references.
- Unit consistency: Numeric values are validated against expected unit types.

Validation failures are logged with diagnostic messages, enabling targeted retry or strategy escalation.

---

## 4.7 Observations and Architectural Alignment

The Hydroscand implementation validates several framework claims:

**Modularity**: Adding new product categories requires only database schema extensions and optional strategy refinements—no changes to orchestration logic.

**Traceability**: Every query response can be traced through strategy and agent logs to specific table cells in source documents, satisfying engineering audit requirements.

**Declarative behavior**: Strategy and agent behavior is defined through database entries, enabling adaptation without code deployment.

**Validation centrality**: The multi-level validation gates prevented propagation of extraction errors (e.g., OCR artifacts in thread notations) to final responses.

### Challenges Encountered

- **Ambiguous table structures**: Some catalog pages contain visually similar but semantically distinct tables requiring context-aware disambiguation.
- **Thread notation variants**: Standards like "G 1/2" and "G1/2" required normalization rules to ensure consistent matching.
- **Multi-page tables**: Tables spanning page boundaries required cross-page reconstruction logic not present in the initial pipeline.

These challenges inform ongoing refinements and suggest directions for enhanced VLM prompting strategies.

---

## 4.8 Summary

The Hydroscand Produktbok application demonstrates that the proposed framework generalizes effectively to industrial catalog extraction. The three-layer architecture cleanly separates extraction, reasoning, and interface concerns. The Relational Control Plane provides the traceability and replay capabilities essential for engineering applications. Strategy and agent libraries enable domain adaptation through declarative configuration rather than code modification. These findings support the framework's claim to domain-agnostic applicability while highlighting domain-specific tuning requirements that merit further investigation.
