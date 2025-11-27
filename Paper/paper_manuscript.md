
# A Domain-Agnostic Agentic Architecture for Structured Extraction of Engineering Knowledge
**Author:** Mehdi Tarkian  
**Affiliation:** Division of Product Realization, Department of Management and Engineering, Linköping University, Sweden  
:contentReference[oaicite:1]{index=1}

---

## Highlights
- Research highlight 1  
- Research highlight 2  

---

# Abstract
Abstract text.

**Keywords:** _not provided_

---

# 1. Introduction

Recent advances in large language models (LLMs) have intensified efforts to capture and operationalize institutional knowledge at scale. Engineering organizations frequently must retrieve precise details about products, components, and processes by cross-referencing:

- specifications  
- standards  
- service manuals  
- engineering change orders (ECO/ECN)  
- part-revision histories  

These tasks normally require years of tacit know-how.

Retrieval-Augmented Generation (RAG) improves access but still suffers from:

- hallucination  
- limited cross-document reasoning  
- difficulty with dense tables, figures, CAD callouts, scanned PDFs  

### Advanced RAG
Methods like **RAPTOR** build hierarchical representations and retrieve at multiple abstraction levels. While helpful, engineering tasks still require:

1. Revision & change awareness  
2. Table & units fidelity  
3. Cross-constraint reasoning across BOMs, ECOs, service bulletins, and standards  
4. Traceability to exact clauses, figures, or table cells  

### Why PDFs and tables remain hard
PDF structure extraction—especially table detection, header reconstruction, and unit normalization—remains a core bottleneck. Tools like PubTables-1M, GROBID, and GROBID-quantities offer partial solutions, but RAG pipelines rarely integrate them deeply.

### Role of Agent Frameworks
Agentic frameworks use tool orchestration, reasoning-and-acting (ReAct), and multi-step planning, but engineering use cases require multiple specialized agents:

- table/units agent  
- revision/lineage agent  
- CAD/PLM agent  
- standards agent  

Managing this complexity demands robust orchestration, retries, validation, state tracking, and observability.

### Purpose of this Study
This work proposes a **generic agentic framework** extending LangGraph with a **domain-agnostic control loop** structured into six coordinated stages:

1. Goal definition  
2. Strategy selection  
3. Agent execution  
4. Agent validation  
5. Strategy validation  
6. Goal validation  

A key innovation: **an SQL-backed Relational Control Plane (RCP)** storing all orchestration artifacts—goals, strategies, agent calls, parameters, outputs, validations—providing persistent state, traceability, deterministic replay, and modularity.

Empirical evaluations show the architecture maintains accuracy of advanced retrieval while reducing hallucination rates through structured validation.

---

# 2. State of the Art

## 2.1 Agentic AI in Manufacturing

Agentic AI systems involve autonomous reasoning, decision-making, planning, and acting. They differ from rule-based AI through:

- multi-agent coordination  
- LLM-enabled reasoning  
- dynamic environment adaptation  

### Use of LLMs in Engineering
Key findings:

- **Nicholson et al. (2025):** GPT-4V successfully interpreted mechanical drawings, extracted dimensions, and generated CAD scripts (CadQuery, FeatureScript, OpenSCAD), though requiring iterative corrective feedback.  
- **Freire et al. (2024):** LLM Q&A over factory docs improved operator query handling but workers still preferred human mentorship.  

### Challenges
1. Hallucination and factual grounding remain persistent.  
2. LLMs have limited context; iterative prompting loses earlier details.  
3. Digital twin integration improves grounding but is complex.  
4. RAG slices help but depend heavily on structured databases and memory stores.  
5. Formal validation layers are rare yet essential.  

### Summary
The field shows rapid progress but existing systems tend to be:

- narrow in scope  
- architecture-rigid  
- prone to hallucination  
- insufficiently grounded  

Future work requires **dynamic agent systems with structured domain knowledge** (databases, digital twins) and **rigorous validation layers**.

---

# 3. Methodology

This work introduces a **generic agentic framework** extending LangGraph with a domain-agnostic, validation-centric control loop.

## Six-Stage Control Loop

1. **Normalize user query into a Goal object**  
   - Defines variables, required evidence granularity, revision scope, uncertainty tolerance.

2. **Select strategy template**  
   Example strategies:  
   - Revision-Aware Spec Lookup  
   - Table-Grounded Numeric Extraction  
   - Cross-Document Conflict Resolution  

3. **Select eligible agents**  
   Agents whose preconditions match current state.

4. **Run local validation checks**  
   - schema completeness  
   - unit normalization  
   - range plausibility  
   - document anchors  
   - error diagnostics  

5. **Test strategy sufficiency**
   - e.g., corroboration by two sources  
   - consistent revisions  
   - no unresolved conflicts  

6. **Goal acceptance**
   - final citation accuracy  
   - correct revision range  
   - uncertainty below threshold  

This separates **progress monitoring** (validation gates) from **capability invocation** (agents).

---

# 3.1 Relational Control Plane (RCP)

The RCP is the persistent orchestration database. It externalizes coordination logic into a normalized relational schema.

### Design-Time (Policy Tables)

- strategy templates  
- agent function templates  
- input–output contracts  
- validation rules  

### Run-Time (Instance Tables)

- each goal instance  
- each strategy instance  
- each agent invocation  
- parameters, outputs, validations  
- diagnostic messages  

### Key Benefits

- **Behavior defined as data**, not hard-coded logic  
- Deterministic replay  
- Dashboard and lineage queries  
- Audit-ready governance  
- Modular integration of new tools (retrievers, PDF parsers, unit normalizers)

This provides **traceability, provenance, and adaptability**.

---

# 3.2 Strategy Library

A strategy is a reusable plan template containing:

1. **Targets:**  
   Variables/evidence needed (value, unit, revision, citation).

2. **Eligible agents:**  
   Ordered or flexible tool sequences (e.g., search → parse → normalize → verify).

3. **Sufficiency conditions:**  
   Examples:  
   - two corroborating sources  
   - explicit revision supersession  

4. **Fallback policies:**  
   - broaden search scope  
   - use hierarchical retrieval  
   - escalate strategy  

---

# 3.3 Agent Library

Agents are modular, atomic operations with:

- declared inputs  
- declared outputs  
- post-conditions  
- side-effect-free execution  

### Examples

- text retrieval  
- hierarchical retrieval  
- table extraction & reconstruction  
- unit normalization  
- revision & lineage checking  
- figure/callout linking  
- keyword expansion  
- table filtering  
- evidence scoring  

Agents feed validated artifacts into strategy targets. Validation gates decide when to proceed or retry.

Because all agents share uniform interfaces, they can be swapped without code changes—improving modularity and reuse.

---

# 3.4 In-Session Instantiation

Execution involves:

1. Creating a **goal instance**  
2. Instantiating a **strategy instance**  
3. Running **agent instances**  

All inputs/outputs are stored as first-class artifacts with:

- citations  
- revision lineage  
- unit normalizations  
- diagnostics  
- intermediate structured tables or passages  

### Benefits

- Minimal in-memory state  
- Deterministic replay  
- Complete traceability from final answer → strategy → agent → clause/cell  
- Updating library entries adapts system behavior without rewriting orchestration code  
- Immediate availability of new strategies/agents  

---

# References
(As extracted from PDF)
- Lewis et al., 2020. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.  
- Huang et al., 2023. Survey on Hallucination in LLMs.  
- RAPTOR (Parthasarathi et al., 2024).  
- PubTables-1M (Smock et al., 2022).  
- GROBID, GROBID-quantities.  
- ReAct (Yao et al., 2022).  
- Toolformer (Schick et al., 2023).  
- LangGraph documentation.  
- Nicholson et al., 2025. VLMs for engineering design.  
- Freire et al., 2024. LLM knowledge sharing in manufacturing.  
- Gkournelos et al., 2024. LLMs in HRC assembly.  
- Singh et al., 2025. LLM + Digital twins for fault handling.  

