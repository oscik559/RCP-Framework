# A Domain-Agnostic Agentic Architecture for Structured Extraction of Engineering Knowledge

**Research Article**

**Oscar Ikechukwu**¹, Mehdi Tarkian¹, Sanjay Nambiar¹, Marie Jonsson¹, Christoffer Brax²

¹ Division of Product Realization, IEI, Linköping University, Linköping, Sweden  
² Saab Surveillance, Saab AB, Linköping, Sweden

*Correspondence: oscar.ikechukwu@liu.se*

---

## Abstract

Engineering organizations increasingly adopt large language models (LLMs) to retrieve facts from heterogeneous technical documentation; however, deployments remain brittle when answers must be grounded to specific sections, pages, and tabular data in documentation. In practice, retrieval-augmented generation and agent pipelines often fail due to hallucinations, weak validation, and limited traceability, especially in table-dense and revision-controlled engineering corpora. This paper presents an applied, domain-agnostic agentic architecture for structured extraction and verification of engineering knowledge. The approach introduces a persistent, SQL-backed Relational Control Plane (RCP) that stores goals, strategies, tool calls, outputs, and validation outcomes as first-class relational entities. The design goal is to integrate and support governance by storing every intermediate artifact and check result. Reasoning is organized as a six-stage loop (goal definition, strategy selection, agent execution, agent validation, strategy validation, and goal validation) that enforces evidence-centric progression and enables deterministic replay and audit-ready provenance. We evaluate the framework on two industrial case studies involving a hydraulic product catalogue and revision-controlled technical documentation. Compared to baseline retrieval and non-validated agent pipelines, the proposed architecture improves citation and revision fidelity, reduces unsupported generations, and provides transparent, queryable execution traces. These results demonstrate a practical pathway for deploying trustworthy generative-AI systems in engineering knowledge management.

**Keywords:** Agentic AI; Engineering Informatics; Large Language Models; Knowledge Engineering

---

## 1. Introduction

Recent advances in large language models (LLMs) have intensified efforts to operationalize institutional knowledge across complex enterprise data ecosystems. Engineering organizations routinely retrieve precise product, component, and process details by cross-referencing heterogeneous documentation—specifications, drawings, standards, service manuals, part-revision histories, and engineering change orders (ECO/ECN)—tasks that traditionally require years of domain expertise. Industrial studies have begun to illustrate the potential of LLM-based tools to support engineering knowledge sharing. For example, Freire et al. developed an LLM-driven Q&A system that integrates factory documentation with expert operator knowledge. The system answers operator queries by searching relevant manuals and reports, significantly accelerating information retrieval in manufacturing settings, while also underscoring the continued need for expert validation.

Retrieval-Augmented Generation (RAG) improves access to such domain knowledge; however, current pipelines remain brittle in engineering contexts. They frequently hallucinate, struggle with multi-document reasoning, and underperform on non-text modalities common in technical documentation—including dense tables, figures, engineering drawings, CAD callouts, and scanned PDFs. Advanced RAG approaches such as RAPTOR construct hierarchical representations of long documents and retrieve information at multiple abstraction levels, improving cross-chunk coherence and reducing irrelevant context. Nevertheless, several challenges persist in engineering applications: (i) revision and change awareness, where answers must reflect the correct revision scope and supersession rules; (ii) table and units fidelity, since critical information often resides in dense tables requiring robust parsing and normalization; (iii) cross-constraint reasoning across bills of materials (BOMs), ECOs, service bulletins, and standards; and (iv) provenance traceability to exact clauses, figures, or table cells for auditability.

Agentic frameworks mitigate some of these limitations by orchestrating tools, multi-step planning, and verification (e.g., ReAct-style reasoning-and-acting; tool-use learning). In engineering contexts, however, no single agent typically suffices. Depending on domain and task, systems must coordinate specialized components—such as a table/units agent for numerical extraction and normalization, a revision/lineage agent for change tracking, a CAD/PLM agent for configuration reasoning, and a standards agent for normative rule interpretation. This coordination significantly increases the burden of managing system state, execution flows, retries, and observability. Frameworks such as LangGraph provide useful abstractions, but production deployments still require explicit state design, graph orchestration, heterogeneous tool integration (e.g., vector stores, OCR systems, table parsers, CAD/PLM APIs), persistence, evaluation, and replay.

This paper presents a domain-agnostic agentic framework for orchestrating multi-agent reasoning workflows across engineering knowledge domains. The central novelty lies in externalizing orchestration state into a relational persistence model backed by SQL. Rather than maintaining transient in-memory execution graphs, all orchestration artifacts—goals, strategies, agent calls, parameters, outputs, and validation outcomes—are stored as structured relational records, enabling deterministic replay, full observability, and audit-ready traceability. By decoupling orchestration policies from retrieval implementations and remaining partially independent of specific vector-store technologies, the framework achieves modularity, adaptability, and operational simplicity.

Empirical evaluations on engineering document retrieval and reasoning tasks demonstrate that the proposed architecture preserves the benefits of multi-step retrieval and tool use while reducing hallucination rates through structured validation. Beyond accuracy improvements, the system produces audit-ready execution traces that support governance and reproducibility in industrial settings where incorrect units, revision scope, or missing provenance can lead to costly downstream errors.

The contributions of this work are threefold:

- A validation-centric agentic architecture with relational persistence enabling deterministic replay and auditability.
- An empirical evaluation on engineering document reasoning tasks demonstrating improved reliability and traceability compared to conventional retrieval pipelines.
- Audit-ready execution traces supporting governance in industrial settings.

---

## 2. Related Work

### 2.1 Agentic AI in Engineering

Agentic AI systems extend beyond one-shot generation by iteratively planning, invoking external tools, and executing intermediate actions toward a goal. Such systems are increasingly investigated in manufacturing and engineering contexts, where autonomous decision-making, goal-oriented action, and multi-agent coordination are required in dynamic environments. In engineering document comprehension specifically, agent-based architectures have been proposed as a practical way to dynamically route queries to specialized agents, highlighting the value of modular architectures for engineering knowledge extraction and interpretation. Empirical work demonstrates both capabilities and limitations: Weibull et al. report near-perfect named entity extraction from industrial diagrams using multimodal LLMs, whereas Li et al. identify persistent issues including specification oversimplification and fabrication when extracting formal specifications from documentation. Controlled field experiments further show that AI-assisted users outperform non-users, although trust in AI outputs remains a barrier to adoption.

Two challenges consistently emerge: hallucination and context limitations. Wei et al. attribute hallucination to internal-state drift caused by incremental context injection and "attention-locking" after multiple interaction rounds. In addition, Xie and Ju highlight the limited domain-specific reasoning ability of general-purpose LLMs and argue that constructing curated models for every engineering subdomain is impractical, motivating structured retrieval mechanisms. Reliability challenges—including temporal inconsistency and limited interpretability—further motivate architectures that enforce structured interaction, persistent state, and verifiable evidence, allowing intermediate reasoning steps to be inspected and validated rather than implicitly assumed.

### 2.2 Document Understanding for Structured Extraction

Engineering knowledge is predominantly captured in documents containing heterogeneous elements: dense tables, technical drawings (figures, flowcharts), algorithms, multi-column layouts, and revision annotations. Extracting structured information from these sources requires layout-aware models that preserve spatial and semantic relationships. Prior work has shown that surface-level text extraction is insufficient, as critical information is encoded in table structure, cross-cell references, figure captions, notes, measurement units, and canonical representations.

Document AI has advanced through transformer-based architectures and specialized recognition models that improve form understanding and information extraction: Xu et al. introduced LayoutLM for joint text–layout modelling, DOTABLER and Table Transformer for table structure recognition, while Safder et al. demonstrated figure parsing methods for semantic enrichment.

Technical documents introduce additional domain-specific complexities, including revision markers that alter content validity, cross-references between drawings and parts lists, and mixed units requiring normalization. While general-purpose document parsers extract text blocks, modern multimodal document parsers combine OCR, layout analysis, and entity linking, but often lose semantic anchors—such as page numbers, notes references, table cell coordinates, and figure callouts needed for auditability. These challenges motivate extraction pipelines that preserve provenance anchors while transforming unstructured documents into queryable relational structures.

### 2.3 Hybrid and Multi-Step Retrieval

Retrieval-Augmented Generation (RAG) has emerged as a foundational mechanism for grounding LLM outputs in external knowledge. However, single-step RAG is insufficient for complex engineering applications requiring multimodal, multi-structural, and multi-document information synthesis. Hybrid approaches have evolved to enrich retrieval with structured knowledge representation: GraphRAG and MDKG-RAG use graph traversal, TaxFlow for legal texts combines metadata indexing with validity filtering—analogous to engineering revision control, HGMem employs external memory capturing higher-order correlations to address the fragmented reasoning that plagues extended retrieval contexts.

Parallel work has framed multi-step retrieval as a sequential decision-making problem rather than a one-shot search operation, addressed through reinforcement learning and planner–executor architectures. Planner–executor architectures decompose complex queries into intermediate sub-goals executed iteratively by specialized reasoning and retrieval components. While effective, these methods are computationally expensive and do not persist intermediate validation outcomes or provide staged verification at multiple steps. This makes it difficult to inspect why a chain succeeded, where it failed, or how it should be replayed and audited in engineering settings—a governance gap that motivates our approach.

### 2.4 Evaluating Multi-Step Reasoning

Traditional question–answering (QA) benchmarks provide partial support for evaluating multi-step reasoning systems. Benchmarks such as OK-VQA, WebQA, and HotpotQA emphasize final answer accuracy, masking failure modes—retrieval errors, step omission, etc.—critical for engineering auditability. While useful for model comparison, they provide little insight into where errors originate in complex pipelines.

More recent benchmarks address these limitations. Ning et al. introduce MC-SEARCH, a framework for agentic multimodal RAG with step-wise annotated chains spanning five reasoning topologies, and propose HAVE verification with process-level metrics (Hit per Step, Rollout Deviation). RAGEval extends this, introducing Completeness, Hallucination, and Irrelevance metrics for scenario-specific RAG evaluation beyond conventional accuracy measures. However, process metrics alone are insufficient; observability requires persistent execution traces for post-hoc analysis, and real-world evaluation must account for trust and validation.

---

The limitations identified in existing approaches—hallucination in agentic systems, loss of provenance in multi-step retrieval, and lack of persistent validation traces—motivate the architectural design presented in the following section. We introduce a validation-centric framework that externalizes orchestration state into a relational persistence model, enabling deterministic replay and complete auditability while maintaining modularity across engineering domains.

---

## 3. Method

Engineering document reasoning requires coordinated execution of specialized agents, structured validation at multiple levels, and complete auditability of reasoning chains. This section presents a domain-agnostic agentic framework that addresses these requirements through a relational persistence model backed by SQL. Unlike conventional agent frameworks that maintain transient in-memory states, the proposed architecture externalizes all orchestration artifacts—goals, strategies, agent invocations, and validation outcomes—into queryable relational records.

The framework operationalizes agentic reasoning through a structured six-stage control loop (Algorithm 1). The loop decouples progress monitoring (validation gates) from capability invocation (functions), making the system robust to partial failures and amenable to targeted improvements.

A distinguishing characteristic of this framework is its **Relational Control Plane (RCP)**. All orchestration artifacts—goals, strategies, function invocations, parameters, outputs, and validations—are persisted in an SQL database rather than maintained as transient in-memory state. This enables deterministic replay, complete observability, and audit-ready traces while decoupling orchestration from specific retrieval technologies.

**Organization.** The remainder of this section is structured as follows. Section 3.1 describes the two-tier data storage model. Section 3.2 introduces the Relational Control Plane (RCP). Sections 3.3 and 3.4 define the Strategy and Function Libraries. Section 3.5 explains in-session instantiation. Section 3.6 presents the strategy selection algorithm and system characteristics.

---

**Algorithm 1: Agentic Reasoning Loop**

```
Input:  User Query Q, Strategy Library L_S, Function Library L_F
Output: Validated Answer A or Failure Reason E

Stage 1: Goal Definition
  G ← Normalize(Q)   // Determine targets, evidence granularity, & validation rules
  RCP.LogGoal(G)

Stage 2: Strategy Selection
  S ← L_S.FindBestMatch(G)   // Select plan template from Policy Tables
  RCP.LogStrategy(S)

Stage 3: Execution Loop
  P ← S.PlanSteps
  for each Step ∈ P:
    f ← L_F.GetFunction(Step.Capability)
    O ← f.Execute(Step.Inputs)
    RCP.LogExecution(f, O)

    Stage 4: Function Validation
    if ¬ ValidateFunction(O):
      retry Step with adjusted parameters or break to fallback

    Stage 5: Strategy Validation
    if ValidateStrategy(S, O):
      break   // Sufficiency criteria met early

Stage 6: Goal Validation
  if ValidateGoal(G, S.FinalOutput):
    return A ← S.FinalOutput
  else:
    backtrack to Stage 2 with broader strategy
    or return E ← "No valid strategy"
```

---

### 3.1 Storing Engineering Data

The foundational phase of the framework is dedicated to knowledge acquisition, in which domain-specific engineering knowledge is systematically harvested from source documentation and converted into structured data instances. These instances are paired with explicit provenance anchors (e.g., page, section, figure, and table-cell references) so that downstream reasoning and validation can remain evidence-grounded.

Engineering documents interleave structured tables, free text, illustrative figures, reference notes, revision markers, and domain-specific notations. To accommodate this heterogeneity, the framework adopts a **two-tier, SQL-based storage model**: a persistent knowledge base that objectifies core engineering data, and a transient in-session cache for run-time data assembly.

**Harvested Database (Objectification Layer).** The Harvested database serves as the canonical repository of engineering knowledge extracted from source documents. Regardless of domain, raw material PDFs, scanned documents, and manuals are converted into a normalized relational form. This process, referred to as *objectification*, ensures that:

(a) semantic structure and entities are represented consistently across documents,  
(b) numerical and unit-bearing fields are stored with canonical types,  
(c) provenance (page, section, figure, or table anchors) is retained, and  
(d) the data becomes amenable to deterministic, query-based retrieval.

**Temporary Database (Session Assembly Layer).** During reasoning, strategy plans often require intermediate aggregation, filtering, or transformation of data that should not modify the persistent knowledge base. The temporary, session-scoped database holds: (a) intermediate subsets produced by search or filtering agents, (b) normalised or reformatted values required for downstream validation, (c) assembled evidence packets combining multiple knowledge sources, and (d) transient artefacts generated during multi-step strategies. The temporary database is strictly short-lived: its contents exist only for the duration of the reasoning episode.

### 3.2 Relational Control Plane

The Relational Control Plane (RCP) serves as the central orchestration database of the proposed framework, externalizing coordination logic from code into a normalized relational schema. Conceptually, the RCP enforces a clear separation between **design-time policy** and **run-time execution**:

- At **design time**, the library tables define the system's capability space—strategies are represented as reusable plan templates, while functions are modeled as atomic operations with declared input–output contracts.
- At **run time**, corresponding instance tables record each concrete goal, strategy, and function invocation, including their parameters, outputs, validation outcomes, and diagnostic messages.

Compared to conventional agentic frameworks, the RCP introduces three fundamental advances:

1. Changes in execution order, eligibility, or capability preference are achieved through updates to policy data rather than through code rewrites.
2. Every decision, artifact, and validation outcome is recorded, enabling deterministic replay, post hoc analysis, and quantitative evaluation of strategy performance.
3. New capabilities or alternative implementations can be added by simply registering them within the RCP library, allowing existing strategies to incorporate them immediately without altering the orchestration graph.

### 3.3 Strategy Library

The Strategy Library contains reusable plan templates that standardize patterns of tool usage, reasoning, and validation across engineering contexts. Each strategy specifies four core components:

- **Targets:** The evidence or variables required for successful completion (e.g., numerical value with units, revision identifier, document citation).
- **Eligible functions:** The permissible computational modules and their preferred execution order (e.g., search → parse → normalize → verify).
- **Sufficiency conditions:** The coverage and consistency requirements for completion (e.g., two corroborating sources, explicit revision supersession).
- **Fallback policies:** Adaptive behaviors when sufficiency is not met (e.g., expand search scope, trigger hierarchical retrieval).

### 3.4 Function Library

The Function Library contains modular, atomic operations that execute the steps defined in strategy plans. Each function is a self-contained, side-effect-free component with declared inputs, outputs, and postconditions. Functions compose dynamically to fulfill strategy steps without modifying the orchestration graph, ensuring modularity and maintainability.

Typical functions include: text retrieval (keyword/semantic search with constraint support), hierarchical retrieval (document tree traversal), table extraction (region detection with cell anchoring), unit normalization (canonical conversion with provenance), revision checking (supersession tracing), figure linking, keyword expansion, table filtering, and evidence scoring.

Because all functions adhere to uniform interface specifications, components can be replaced without modifying orchestration logic, ensuring interoperability and adaptability across engineering domains.

### 3.5 In-Session Instantiation

At runtime, design-time templates are instantiated as session-scoped records. For every user query, the controller creates a goal instance with explicit acceptance criteria and then materializes a strategy instance selected from the Strategy Library. Within this strategy context, the controller dynamically instantiates one or more functions from the Function Library. Each instantiation records its parametrization, inputs consumed, outputs produced, and the results of function-, strategy-, and goal-level validations.

The in-session tables serve as a normalized execution ledger. Inputs and outputs are stored as first-class artifacts linked to their originating strategy and agent instances, together with citations, revision lineage, unit normalizations, and diagnostic messages. The orchestration graph maintains only stable identifiers (e.g., current goal, strategy, and function IDs), while all heavy artifacts—retrieved passages, structured tables with cell anchors, intermediate calculations, and validation reports—reside in the RCP. This arrangement enables deterministic replay and post hoc inspection, supports fine-grained provenance from final answers back to specific clauses or table cells, and provides a coherent basis for evaluation and governance.

Beyond runtime traces, the framework maintains declarative schemas for function inputs and outputs. `FunctionParametersLibrary` and `FunctionOutputLibrary` define the expected keys, types, and semantics for each registered function. At execution time, these schemas validate records written to `FunctionParametersInSession` and `FunctionOutputInSession`, enabling early detection of malformed inputs, missing fields, or incompatible outputs before downstream functions are invoked.

Because the controller reads policies from the libraries and writes outcomes to the in-session ledger, behaviour can be adapted by updating library entries rather than rewriting orchestration logic. New strategies or functions become immediately available for instantiation once registered, and their inputs/outputs are automatically captured under the same schema. In effect, the RCP operationalizes a data-driven "goal → strategy → agent → validation" loop: strategies and functions defined in the libraries are realized as concrete, auditable instances, and all inputs, outputs, and validations are persistently recorded, ensuring consistent state management and traceable multi-agent reasoning across domains.

### 3.6 Strategy Selection and System Characteristics

The controller selects strategies through a rule-based matching algorithm that evaluates goal attributes against strategy preconditions. Strategy templates declare eligibility criteria as structured predicates over goal features:

- **Entity recognition:** Does the query contain a component identifier?
- **Attribute type:** Is the target a simple lookup, comparison, or aggregation?
- **Evidence requirements:** Does the goal require revision awareness, cross-document reasoning, or multimodal synthesis?
- **Data availability:** Are authoritative documents identified, or is exploratory search required?

The matching algorithm iterates through strategy templates in priority order, evaluating each template's preconditions against the goal instance. The first strategy whose preconditions are satisfied is selected and instantiated. If no strategy matches, the controller defaults to a generic exploratory strategy or returns a failure diagnostic.

---

## 4. Domain Application

This section presents two industrial applications used to evaluate the proposed framework. Case I (Hydroscand) addresses catalogue-style extraction from dense, multilingual tables with typographic variation. Case II (SAAB) evaluates query-driven reasoning over revision-controlled engineering documents with heterogeneous layouts and applicability constraints.

### 4.1 Case I: Industrial Hydraulic Products Catalog (Hydroscand AB)

Industrial hydraulic systems rely on extensive product catalogues that consolidate specifications for hoses, fittings, and coupling assemblies. These multi-page documents encode critical attributes such as dimensions, pressure ratings, reinforcement structures, material compositions, and thread standards. The *Hydraulic Produktbok*, a widely used Nordic fluid-power reference from Hydroscand AB, is representative of this class: it presents chapter-organised product families, construction descriptions, and dense specification tables spanning numerous variants within each product line.

The catalogue's structure poses notable challenges for automated knowledge extraction. Variant-level data appear in compact tables with merged cells, multi-row headers, mixed unit conventions, and visually implied hierarchies. Thread standards (BSP/G, JIC, ORFS, NPTF) depend on subtle typographic distinctions that OCR and naive PDF parsers often distort. Free-text descriptions (entirely in Swedish) use specialised terminology that impedes generic retrieval models.

#### Layer 1: Document Pre-processing/Extraction (Case I)

The extraction layer converts source documents into a normalized relational database (`harvested.db`). Each page is rendered at high resolution to preserve typographic fidelity—critical for distinguishing notation spacing (e.g., "G 1/2" vs. "G1/2"), sub/superscripts, and unit annotations that carry semantic meaning.

Parsed content is inserted into a relational schema: *categories* (e.g., Högtrycksslang, Presskopplingar), *families* (e.g., Kappaflex 2K, T9090) and *product-level variants* (e.g., 1105-10-04, 1059-00-16). The objective is not merely to extract product data, but to reconstruct the catalogue's implicit structure: the hierarchical organisation of categories and product families, the fine-grained geometry of specification tables, and the contextual metadata that defines material properties, thread standards, and operating limits.

#### Layer 2: Agentic Reasoning (Case I)

The agentic reasoning layer operationalises the six-stage control loop. A user query is normalised into a structured *goal instance* with explicit evidence requirements. The controller then selects an appropriate *strategy instance* and executes an ordered *function plan*. All orchestration artifacts are persisted in the relational control plane (`agentic.db`).

**Strategy templates** for this domain are summarized below:

| ID | Strategy | Description | Plan Steps | Sufficiency Condition |
|----|----------|-------------|------------|-----------------------|
| 1 | *Specification Lookup* | Retrieve a known specification from an identified product code. | Extract product code → Query database → Extract attributes → Analyze with LLM | Attribute found and unit normalized. |
| 2 | *Contextual Product Search* | Identify candidate products matching textual or semantic constraints. | Extract requirements → Semantic search → Filter items → Extract attributes → Analyze with LLM | At least one valid product returned. |
| 3 | *Compatibility Check* | Assess coupling or thread compatibility between two hydraulic components. | Extract component specifications → Match standards → Check dimensional compatibility → Analyze with LLM | Standards matched; no dimensional conflict. |
| 4 | *Family Summary* | Aggregate specification data across all variants within a product family. | Retrieve family variants → Extract attributes → Aggregate results → Analyze with LLM | Full variant set retrieved and schema consistent. |

**Function library** for the hydraulic catalogue domain:

| ID | Function Name | Purpose | Artifact Produced |
|----|--------------|---------|-------------------|
| 1 | `func_extract_products` | Retrieve candidate products using keywords and filters. | List of product codes with summary specifications. |
| 2 | `func_filter_by_attribute` | Narrow a product list by applying attribute constraints. | Filtered list satisfying the specified constraints. |
| 3 | `func_get_product_details` | Retrieve complete specifications and provenance for a given product. | JSON object with metadata and catalog page reference. |
| 4 | `func_extract_attributes` | Extract target attribute values from a product specification. | Attribute values with units and citations. |
| 5 | `func_normalize_units` | Convert values to canonical units while preserving original formats. | e.g., 420 bar → 42 MPa. |
| 6 | `func_analyse_data` | Compose the final answer with citations and verified source trace. | Grounded explanation linked to catalog data. |
| 7 | `func_extract_product_code` | Identify and validate a product identifier from a free-text query. | Validated product code (e.g., 4201-16-16). |

Notably, `func_analyse_data`[^1] performs a structured LLM synthesis over verified intermediate artifacts. It is instructed to preserve catalogue terminology (e.g., "Arbetstryck", "Gängtyp"), avoid unsupported claims, and reference source-provenance fields. All other functions operate deterministically over structured records (from `harvested.db`), enabling validation gates to intercept failures before an answer is returned.

[^1]: For clarity, human-readable function labels (e.g., Analyse With LLM) are mapped internally to registered callable identifiers (e.g., `func_analyse_data`) defined in the Function Library.

These functions adhere to a standardized interface (`success: bool, result: dict`), enabling orchestration via LangGraph without bespoke code. As a result, adding new capabilities (e.g., `func_check_temperature_range`) involves no orchestration modification—only policy entry registration.

#### Layer 3: Application-Level Interaction (Case I)

The application layer exposes the reasoning system through a Flask-based web interface. It accepts free-form queries, which are normalized and submitted to the controller as goal instances. The interface provides real-time visualizations of the reasoning process, including progress through strategy stages, intermediate agent outputs, and final structured answers enriched with provenance annotations.

#### Worked Example: End-to-End Execution (Case I)

To illustrate end-to-end behaviour, this subsection traces a representative specification query:

> *"Vilken gängstorlek har en 4201-16-16?"*  
> (*"What is the thread size of 4201-16-16?"*)

The system must: **(i)** recognise the product code, **(ii)** retrieve the corresponding catalogue record, **(iii)** extract the requested attribute (thread size), and **(iv)** generate a grounded response.

**Goal definition:**

| Field | Value |
|-------|-------|
| GoalID | `1` |
| SessionID | `083` |
| GoalName | `Main goal` |
| Target | `Product specification` |
| Validation | `Thread size resolved for identified product` |
| Description | `Determine the standard thread size of a 4201-16-16 coupling` |
| GoalSuccess | `NULL` |

**Strategy selection:**

| Field | Value |
|-------|-------|
| StrategyID | `1` |
| GoalID | `1` |
| StrategyName | `Specification Lookup` |
| Target | `Product specification` |
| PlanSteps | `Extract product code; retrieve product details; extract attributes; analyse with LLM` |
| Sufficiency | `Attribute found and unit normalized` |
| StrategySuccess | `NULL` |

**Function execution & validation:**

*Function 1 – Extract Product Number:*

| Field | Value |
|-------|-------|
| FunctionID | `1` |
| StrategyID | `1` |
| FunctionName | `func_extract_products` |
| Inputs | `Query string` |
| Outputs | `Keyword Output = 4201-16-16` |
| ValidationResult | `Output non-empty; format valid` |
| FunctionSuccess | `1` |

*Function 2 – Query Database:*

| Field | Value |
|-------|-------|
| FunctionID | `2` |
| StrategyID | `1` |
| FunctionName | `func_get_product_details` |
| Inputs | `Keyword Output = 4201-16-16` |
| Outputs | `Product record; count = 1` |
| ValidationResult | `count > 0; count and format valid` |
| FunctionSuccess | `1` |

*Function 3 – Extract Attributes:*

| Field | Value |
|-------|-------|
| FunctionID | `3` |
| StrategyID | `1` |
| FunctionName | `func_extract_attributes` |
| Inputs | `Product specification record` |
| Outputs | `Extracted attributes: gängstorlek = G1"` |
| ValidationResult | `Attribute present and non-empty` |
| FunctionSuccess | `1` |

*Function 4 – Analyse With LLM:*

| Field | Value |
|-------|-------|
| FunctionID | `4` |
| StrategyID | `1` |
| FunctionName | `func_analyse_data` |
| Inputs | `Query and extracted attributes` |
| Outputs | `Natural-language answer stating thread size` |
| ValidationResult | `Output non-empty; well-formed` |
| FunctionSuccess | `1` |

This worked example demonstrates how goal satisfaction emerges from validated, sequential agent execution, with all intermediate artifacts persisted in the Relational Control Plane (RCP).

---

### 4.2 Case II: Revision-Controlled Aerospace Documentation (Saab AB)

While the first case addressed a semi-structured product catalogue, this second application focused on query-driven interaction with a corpus of technical manuals where cross-document consistency and revision fidelity are critical. This study was conducted in collaboration with Saab AB — a leading Swedish aerospace and defense company.

Engineering documentation in this domain differs fundamentally from catalog-style product data, requiring reasoning across multiple, multilingual, heterogeneous documents, with relevant information distributed across textual, tabular, and graphical elements.

*In compliance with confidentiality requirements, proprietary identifiers, document titles, part numbers, and content values shown in this case study have been anonymized or abstracted.*

#### Layer 1: Document Pre-processing/Extraction (Case II)

Source documentation spans heterogeneous formats and layouts, including narrative requirements, dense tables, and figure-referenced descriptions. During ingestion, each document is represented as linked relational units capturing: (i) document identity and revision markers, (ii) section hierarchy, and (iii) modality-specific artifacts (text passages, table fragments, and figure-referenced elements).

#### Layer 2: Agentic Reasoning (Case II)

Case II reuses the same six-stage goal–strategy–agent control loop. No architectural modifications were required; instead, the framework is instantiated through a richer set of strategy templates and functions tailored to document-centric reasoning.

**Strategy templates** for Case II:

| ID | Strategy | Description | Plan Steps | Sufficiency Condition |
|----|----------|-------------|------------|-----------------------|
| 1 | *Simple Lookup* | Deterministic retrieval from a single authoritative document. | Extract product code → Find latest document → Table search → Filter table → Assemble table → Analyse with LLM | Requested attribute resolved with supporting evidence. |
| 2 | *Enhanced Lookup* | Multi-stage table reasoning with contextual filtering and aggregation. | Extract product code → Table search → Filter table → Assemble table → Analyse with LLM | Consistent result derived across candidate records. |
| 3 | *Parallel Enhanced Lookup* | Latency-aware strategy executing independent steps concurrently. | Extract product code → Find latest document → [Table search ∥ Document search] → Filter table → [Analyse with LLM ∥ Convert units] → Aggregate results | Requested attribute resolved and validated. |
| 4 | *Visual Layout Generation* | Multimodal retrieval and synthesis of layout-level information. | Extract product code → Retrieve image asset → Generate visual layout → Analyse with LLM | Layout produced and grounded in source document. |

*Note: Parallel steps are indicated with the ∥ symbol.*

**Function library** for the SAAB documentation case:

| ID | Function Name | Purpose | Artifact Produced |
|----|--------------|---------|-------------------|
| 1 | `func_extract_product_code` | Identify and validate a product or component identifier. | Validated identifier token. |
| 2 | `func_find_latest_document` | Select the most recent applicable document revision. | Document surrogate ID. |
| 3 | `func_table_search` | Locate candidate tables within a document. | Table records and metadata. |
| 4 | `func_filter_table` | Apply rule-based and semantic filters to tabular data. | Filtered table rows. |
| 5 | `func_assemble_table` | Merge and normalize table fragments into a unified structure. | Structured table artifact (JSON). |
| 6 | `func_generate_visual_layout` | Produce a schematic or layout-level representation from document figures. | Rendered layout artifact. |
| 7 | `func_analyse_data` | Synthesize intermediate artifacts into a grounded natural-language response. | Final answer text with trace context. |

#### Worked Example: End-to-End Execution (Case II)

**Goal instance (anonymized):**

| Field | Value |
|-------|-------|
| GoalID | `G_01` |
| SessionID | `S_XX` |
| Target | `Engineering attribute` |
| Validation | `Attribute resolved with document provenance` |
| Description | `Determine attribute X for component COMP_[ID-01]` |
| GoalSuccess | `NULL` |

**Strategy instance:**

| Field | Value |
|-------|-------|
| StrategyID | `STR_01` |
| GoalID | `G_01` |
| StrategyName | `Simple Lookup` |
| PlanSteps | `Extract product code; find latest document; table search; filter table; assemble table; analyse with LLM` |
| Sufficiency | `Attribute resolved with supporting evidence` |
| StrategySuccess | `NULL` |

Execution proceeds through the ordered function plan; all steps are logged in the RCP. Complete parameter and output records are provided in the appendix.

---

## 5. Evaluation

### 5.1 Experimental Setup

We evaluate the proposed RCP-based agentic framework on two industrial case studies using an annotated query set of 50 technical questions, comparing against two architectural baselines:

(i) a standard retrieval-augmented generation (RAG) pipeline (retrieve top-*k* → generate), and  
(ii) a non-persistent agentic pipeline capable of iterative tool use but without the structured relational state persistence or multi-stage validation gates of the proposed RCP framework.

All methods operate over the same harvested document corpus (`harvested.db`). To ensure consistency, all LLM-based reasoning and generation tasks utilize the *Llama3.2:latest* model (hosted locally via Ollama) with a temperature of 0.0 to promote deterministic outputs. For retrieval-centric steps, documents are segmented into chunks of *800 characters* with an *overlap of 100 characters*. Dense retrieval is performed using *qwen3-embedding:latest* embeddings stored in an in-memory ChromaDB vectorstore, returning the *top-5 chunks* per query.

The non-persistent agentic baseline is granted a maximum of *5 reasoning iterations* per query, invoking the same tool set as the proposed method (e.g., table search, attribute extraction), but maintaining only transient in-memory state.

The implementation code for both case studies is publicly available on GitHub:  
- [Hydroscand Case Study](https://github.com/oscik559/Hydroscand_Produktbok)  
- [Saab Case Study](https://github.com/oscik559/Project_Saab)

### 5.2 Quantitative Metrics

Across both case studies, we report:

(a) *answer correctness* against the annotated reference set;  
(b) *citation accuracy*, defined as whether the cited passage or table cell contains the claimed fact/value;  
(c) *unit fidelity*, including correct normalization and conversions; and  
(d) *operational cost*, measured in end-to-end latency and token/compute usage.

*Hallucination rate* is defined as the fraction of responses containing at least one factual claim not supported by the retrieved evidence.

#### 5.2.1 Performance

Against a dataset of ~50 catalog pages containing 1,628 product variants across 168 families for Case I, we compared the RCP system against the baselines for a set of 40 human-annotated engineering queries.

| Metric | RAG | Agentic (No RCP) | **RCP (Proposed)** |
|--------|-----|------------------|-------------------|
| Answer Correctness | 50.0% | 10.0% | **59.2%** |
| Citation Accuracy | 48.0% | 10.0% | **32.7%** |
| Unit Fidelity | 78.0% | 62.0% | **73.5%** |
| Hallucination Rate ↓ | 22.0% | 42.0% | **24.5%** |

> ⚠️ *Note: Table not finalized — evaluation is being remade.*

The RCP framework achieves a 59.2% answer correctness rate compared to 50.0% for the RAG baseline and 10.0% for the non-persistent agentic baseline. The Agentic (No RCP) baseline exhibited significant instability, often failing to terminate or fabricating database errors after a single failed attempt. The RCP framework's validation gates effectively intercepted such failures.

#### 5.2.2 Operational Cost

| Metric | RAG | Agentic (No RCP) | **RCP (Proposed)** |
|--------|-----|------------------|-------------------|
| Avg. Latency (s) | 4.40 | 4.03 | 12.57 |
| Avg. Function Calls | — | 2.1 | 4.0 |
| Avg. Tokens per Query | 390 | 1,230 | N/A* |

> *Token count for the RCP was uninstrumented for this evaluation iteration.  
> ⚠️ *Note: Table not finalized — evaluation is being remade.*

The increased reliability of the RCP framework comes at the cost of higher operational latency (avg. 12.57s — approximately 3× higher than baselines). This overhead is directly attributable to the six-stage control loop, which involves multiple LLM-based reasoning steps and iterative tool execution.

### 5.3 Error Analysis

Appendix Tables C.1 and C.2 list sample queries from the annotated sets used in this section. Test queries were received from respective company engineers with no involvement in framework development, to prevent evaluation leakage. Each query is assigned a difficulty tier:

- **Easy:** single table lookup
- **Medium:** cross-field inference or semantic matching
- **Hard:** multi-document reasoning or domain-specific disambiguation

The primary error taxonomy for RAG baseline failures:

(i) **Hallucination** — the model asserts a specific value not present in any retrieved chunk.  
(ii) **Partial answer** — a correct product family is identified but required specificity is absent.  
(iii) **Field-name mismatch** — the correct source table is retrieved but the query term does not match the column header literally.

The Agentic (No RCP) baseline demonstrated a paradox of high latency efficiency (avg. 3.59s) but extreme reasoning loop instability, resulting in a 42.0% hallucination rate and only 10.0% accuracy. Unlike the RAG baseline, which primarily failed due to retrieval context limitations, the non-persistent agent often struggled with structured tool execution or fabricated product details when reasoning chains became non-linear or database lookups returned multi-row JSON structures. The RCP Framework mitigated these failure modes by enforcing explicit schema validation on tool outputs and requiring strategy-level sufficiency checks, achieving the highest accuracy at 59.2%. Our analysis indicates that the 24.5% hallucination rate in the RCP framework is primarily due to LLM-synthesis errors in the final stage where validated facts are converted to natural language, rather than infrastructure-level state loss.

---

## 6. Discussion and Limitations

The evaluation demonstrates a clear trade-off: the RCP improves reliability and traceability of LLM-based retrieval in engineering settings, but at measurable computational cost. Average latency rises from approximately 4 s in lightweight pipelines to 12.57 s with the RCP, reflecting additional function calls, validation checkpoints, and persistence of intermediate artifacts.

In both case studies, the baselines occasionally produced confident but incorrect outputs, particularly in revision-controlled scenarios. In contrast, the RCP gates progression by requiring schema validity, provenance completeness, and plausibility checks before synthesis. This shifts system behaviour from *generate–then–justify* toward **verify–then–summarize**. Rather than emitting unsupported values, the system fails explicitly when sufficiency conditions are unmet. In engineering contexts, explicit failure is preferable to silent misinformation.

A practical implication concerns scalability. Because goals, strategies, function invocations, and validation outcomes are stored as relational entities, inspection, error attribution, and replay become database queries rather than bespoke logging implementations.

**Limitations:**

First, system reliability depends on upstream data extraction. OCR errors, poor table reconstruction, and ambiguous typography may propagate into the harvested database and constrain downstream reasoning. The RCP prevents unsupported synthesis but cannot correct malformed source data.

Second, validation predicates require careful tuning. Overly strict predicates increase retries and latency, while overly permissive predicates risk allowing subtle applicability or revision errors to pass.

Third, the evaluation was limited to two industrial domains. Broader benchmarking across additional document genres would strengthen generalizability.

Finally, the current implementation models agent capabilities as canonical functions registered in a structured *function library*. While this supports deterministic execution, it introduces integration overhead when extending to new domains. Emerging skill-based abstractions—declarative SKILL.md specifications—define modular, discoverable capability manifests containing metadata and structured guides. Integrating such skill specifications with relational validation and persistent artifact tracking could reduce integration friction while preserving governance and traceability guarantees.

---

## 7. Conclusions

This study presented a domain-agnostic agentic architecture for structured extraction and verification of engineering knowledge. The core contribution is a validation-centric, six-stage control loop integrated with a persistent, SQL-backed Relational Control Plane that records goals, strategies, agent executions, artifacts, and validation outcomes as relational entities.

Across two industrial case studies—hydraulic product catalogues and revision-controlled technical documentation—the framework reduced hallucination while preserving engineering-critical fidelity, including unit correctness, applicability scope, and provenance granularity. By externalizing orchestration state as persistent data rather than embedding it solely in transient execution logic, the architecture enables auditability, deterministic replay, and systematic performance analysis.

**Future work** will focus on (i) expanding validation toward cross-source consistency checking, including conflict detection and supersession-aware reconciliation across revisions; (ii) improving multimodal grounding for tables and figures through tighter cell- and region-level anchoring; and (iii) developing standardized evaluation suites that score not only answer correctness, but also provenance completeness, revision fidelity, and replay determinism.

---

## Acknowledgements

The authors gratefully acknowledge the support of the Swedish Innovation Agency (Vinnova), which made this research possible. We also thank the industrial partners who provided representative technical documentation and valuable domain feedback.

During the preparation of this manuscript, the authors used ChatGPT-5 solely as a language assistance tool to improve clarity and readability. All scientific content, analysis, and conclusions are the responsibility of the authors.

## Author Contributions

**Oscar Ikechukwu:** Formal analysis, Methodology, Software, Validation, Visualization, Writing – original draft, Writing – review & editing;  
**Mehdi Tarkian:** Conceptualization, Methodology (framework and architecture design), Formal analysis (theoretical framework development), Supervision, Writing – review & editing;  
**Sanjay Nambiar:** Investigation, Writing – review & editing;  
**Marie Jonsson:** Writing – review & editing.

## Disclosure Statement

No potential conflict of interest was reported by the author(s).

## Funding

This work was supported by Vinnova under Grant [2024-01420] - Data Automation and Retrieval Technology (DART) as part of the research program 'Advanced digitalization - Enabling technologies'.

## ORCiD

- **Oscar Ikechukwu:** https://orcid.org/0009-0000-4905-2344  
- **Mehdi Tarkian:** https://orcid.org/0009-0003-6305-8621  
- **Sanjay Nambiar:** https://orcid.org/0000-0003-1745-3869  
- **Marie Jonsson:** https://orcid.org/0000-0002-6079-2359

## Data Availability Statement

The data that support the findings of this study are not publicly available due to confidentiality agreements with the industrial partners. The framework code used in this study is publicly available at https://github.com/oscik559/Hydroscand_Produktbok.git. Anonymized artifacts and derived data may be made available by the corresponding author upon reasonable request.

---



---

## Appendix A: Prompts

This appendix presents canonical prompt templates with formal operators from Algorithm 1 used in the goal–strategy–function control loop. Each template corresponds to a typed state transition in the RCP and persists structured outputs into the underlying database schema. Runtime placeholders appear as `{variable_name}`.

### A.1 Goal Definition (Stage 1)

Stage 1 implements the mapping *f_G : Q → G*, where *G* satisfies schema constraint *S_G* and is persisted in the `Goal` table.

```
SYSTEM:
    Expert Goal-definition assistant for user queries.
    - Extract a structured goal from the user query.
    - Define the validation metadata for the goal structure.
    
    Required JSON:
    {"goal_description": "user's technical intent",
     "expected_content_types": ["e.g., product_specs, lookup_values, technical_measurements etc"],
     "key_terms": ["domain-specific technical terms"],
     "success_indicators": ["criteria to validate a satisfactory answer"]}
    
USER:
    USER QUERY: {query}
```

### A.2 Strategy Selection (Stage 2)

Stage 2 implements *f_S : (Q, G, L_S, F) → S*, where *L_S* is the Strategy Library and *F* is the set of previously attempted strategies. Constraint: *S ∈ L_S \ F*. The selected strategy is persisted in the `Strategy` table.

```
SYSTEM:
    Strategy planner for a technical documentation system.
    
    - Select EXACTLY ONE strategy from AVAILABLE STRATEGIES
    - Use the EXACT case-sensitive name
    - Do NOT select any strategy listed under FORBIDDEN.
    
    Return valid JSON only:
    {"StrategyName": "[EXACT name]",
     "StrategyTarget": "deep search",
     "Rationale": "BRIEF justification"}

USER:
    USER QUERY: {query}
    CURRENT GOAL: {goal_desc}
    FORBIDDEN: {tried_readable}
    AVAILABLE STRATEGIES: {lib_block}
```

### A.3 Evidence-Constrained Synthesis (Stages 3–5)

Stages 3–5 implement *f_A : (E, Q) → A*, where *E* is the assembled evidence set. Constraint: *A ⊆ E* (no unsupported claims). Outputs are logged in the `FunctionOutput` and execution-trace tables.

```
SYSTEM:
    EXPERT technical data analyst.
    Analyze the compiled data and provide clear, precise answers to user
    queries, ONLY with the provided DATA CONTEXT. If information is
    missing, state so explicitly.
    
    - Cross-reference codes with spec tables
    - Retrieve via linking fields
    - Apply semantic field mapping
    - Return exact specifications
    
    Field mappings:
    {- contact count  -> Number of contacts # size
     - shell size     -> Shell size
     - cable diameter -> Max Cable entry
     - torque         -> fields with "torque" or "Nm"}

USER:
    DATA CONTEXT: {combined_context}
    USER QUERY: {query}
```

### A.4 Goal Validation (Stage 6)

Stage 6 implements the acceptance predicate *f_V : (G, A) → c ∈ [0,1]*, where *c* is a confidence score used by the RCP termination logic. If *c ≥ τ*, the goal is marked successful.

```
SYSTEM:
    You are a goal-level evaluator for technical queries.
    Return ONLY valid JSON in the form:
    {"confidence": 0.0}
    
    Confidence Scoring:
    - 0.8–1.0 = complete, detailed answer
    - 0.6–0.7 = good coverage of main aspects
    - 0.3–0.5 = partial / insufficient
    - 0.0–0.2 = no meaningful answer

USER:
    USER QUERY: {query}
    GOAL DEFINITION: {goal_definition}
    FINAL OUTPUT: {full_evidence}
```

All prompt inputs and structured outputs are persisted in the RCP execution-trace schema, enabling deterministic replay, failure analysis, and post-hoc validation.

---

## Appendix B: Sample Query Sets (Hydroscand Case)

The following 50 queries were curated from the Hydroscand product database to evaluate the RAG baseline, the Agentic (No RCP) pipeline, and the proposed RCP framework. The final three columns report primary error classes according to the taxonomy defined in Section 5.3.

**Error class key:** 🟢 Correct &nbsp;|&nbsp; 🟡 Partial Answer &nbsp;|&nbsp; 🔴 Hallucination &nbsp;|&nbsp; 🔵 Field-Name Mismatch &nbsp;|&nbsp; ⚪ Parser Error

| ID | Query | GT | RAG | Agentic | RCP (Proposed) |
|----|-------|----|-----|---------|----------------|
| 1 | I'm looking for the specific working pressure rating in MPa for the Hydroscand hose 1103-03-04. Can you find it? | 29.0 MPa | 🔵 Field-Name Mismatch | 🟡 Partial Answer | The Hydroscand catalogue entry for article 1103-03-04 specifies a working pressure rating of 29.0 MPa. |
| 2 | We need to verify the maximum outer diameter (YD mm) for the KAPPAFLEX 1 model 1103-03-08. What is it? | 19.0 mm | 🟢 Correct | 🔴 Hallucination | For KAPPAFLEX 1, article 1103-03-08, the documented outer diameter (YD) is 19.0 mm. |
| 3 | Can you tell me the internal diameter (ID) of the 1103-03-12 hydraulic hose in fractional inches? | 3/4" | ⚪ Parser Error | 🔴 Hallucination | The Hydroscand record for article 1103-03-12 reports an internal diameter corresponding to 3/4 inch. |
| 4 | What is the tightest bend radius we should allow for the 1 1/4" hose with article number 1103-03-20? | 300 mm | 🟢 Correct | 🔴 Hallucination | Article 1103-03-20 (1 1/4") has a specified minimum bend radius of 300 mm. |
| 5 | I need to compare the weight per meter between the 1103-03-04 and 1103-03-16 hoses. Which one is heavier? | 0.18 vs 0.82 kg/m | 🔴 Hallucination | 🟡 Partial Answer | The unit weights are 0.18 kg/m (1103-03-04) and 0.82 kg/m (1103-03-16); therefore, 1103-03-16 is heavier. |
| 6 | Within the 1105-10 series, which specific article number should I use if I need exactly 45.0 MPa working pressure? | 1105-10-04 | 🔴 Hallucination | 🟡 Partial Answer | Within the 1105-10 series, the article rated at 45.0 MPa working pressure is 1105-10-04. |
| 7 | Check the minimum and maximum lengths for the 1105-10-04-30 reel configuration. | 170–230 | 🟢 Correct | 🟢 Correct | Reel configuration 1105-10-04-30 specifies a minimum length of 170 and a maximum length of 230. |
| 8 | What's the internal diameter in millimeters for the 3/4" 1105-10-12 hose? | 19.0 mm | 🟡 Partial Answer | 🟡 Partial Answer | For article 1105-10-12 (3/4"), the internal diameter is 19.0 mm. |
| 9 | Can you find the specific weight in kg/m for the 1" 1105-10-16 hose? | 0.79 kg/m | 🟡 Partial Answer | 🟡 Partial Answer | Article 1105-10-16 (1") has a specified unit weight of 0.79 kg/m. |
| 10 | If I switch from 1105-10-04 to 1105-10-08, how much larger will the bend radius be? | +45 mm | 🔴 Hallucination | 🟡 Partial Answer | Switching from 1105-10-04 (45 mm) to 1105-10-08 (90 mm) increases the bend radius by 45 mm. |
| 11 | What is the maximum pressure limit for a Hydroscand 1105-63-04 hose? | 45.0 MPa | 🔴 Hallucination | 🔴 Hallucination | Article 1105-63-04 defines a maximum working pressure of 45.0 MPa. |
| 12 | I'm looking at reels 1105-63-04-30 and 1105-63-08-30. Are there any differences in the hose dimensions? | 1/4" vs 1/2" | 🟡 Partial Answer | 🟡 Partial Answer | 1105-63-04-30 corresponds to 1/4", while 1105-63-08-30 corresponds to 1/2"; the hose dimension differs accordingly. |
| 13 | What is the minimum recommended bend radius for the 1105-63-16 model? | 210 mm | 🔴 Hallucination | 🟡 Partial Answer | The minimum recommended bend radius for article 1105-63-16 is 210 mm. |
| 14 | How much does a meter of the 1 1/4" hose 1105-63-20 weigh? | 1.52 kg/m | 🟡 Partial Answer | 🔴 Hallucination | Article 1105-63-20 (1 1/4") has a unit weight of 1.52 kg/m. |
| 15 | Can you verify the working pressure rating for article 1105-21-04? | 45.0 MPa | 🟢 Correct | 🟡 Partial Answer | The working pressure rating for article 1105-21-04 is 45.0 MPa. |
| 16 | What is the external diameter (YD) of the 1105-21-16 variant? | 35.6 mm | 🟢 Correct | 🟢 Correct | The specified outer diameter (YD) for article 1105-21-16 is 35.6 mm. |
| 17 | I need to know the ID in inches for the 1105-43-06 Hydroscand model. | 3/8" | 🟡 Partial Answer | 🟡 Partial Answer | The internal diameter for article 1105-43-06 is 3/8 inch. |
| 18 | What is the longest reel length I can get for article 1104-17-04-30? | 260 | 🟡 Partial Answer | 🔴 Hallucination | Reel configuration 1104-17-04-30 has a maximum reel length of 260. |
| 19 | Find the weight per meter for the 1" configuration of 1104-17-16. | 1.17 kg/m | 🔴 Hallucination | 🔴 Hallucination | Article 1104-17-16 has a unit weight of 1.17 kg/m for the 1" configuration. |
| 20 | What is the nominal working pressure recorded for the 1/4" 1102-14-04? | 40.0 MPa | 🟢 Correct | 🔴 Hallucination | For article 1102-14-04 (1/4"), the nominal working pressure is 40.0 MPa. |
| 21 | Can you find the working pressure for article 1106-73-08? | 47.0 MPa | 🟢 Correct | 🔴 Hallucination | Article 1106-73-08 has a specified working pressure rating of 47.0 MPa. |
| 22 | What is the outer diameter specification for 1106-73-10? | 28.8 mm | 🔴 Hallucination | 🟢 Correct | The catalogue specifies an outer diameter (YD) of 28.8 mm for article 1106-73-10. |
| 23 | Check the bending radius for article 1106-73-12 in the catalog. | 260 mm | 🟢 Correct | 🟡 Partial Answer | The documented bending radius for article 1106-73-12 is 260 mm. |
| 24 | I need the weight per meter for the 1106-73-16 hose. | 1.99 kg/m | 🔴 Hallucination | 🔴 Hallucination | Article 1106-73-16 has a specified unit weight of 1.99 kg/m. |
| 25 | Identify the working pressure rating for the 1106-43-08 variant. | 47.0 MPa | 🟢 Correct | 🔴 Hallucination | The working pressure for article 1106-43-08 is 47.0 MPa. |
| 26 | What is the geometric outer diameter for article 1106-43-12? | 32.5 mm | 🔴 Hallucination | 🟡 Partial Answer | The specified outer diameter for article 1106-43-12 is 32.5 mm. |
| 27 | Are the working pressures of 1106-73-08 and 1106-43-08 the same? | 47.0 MPa | 🔴 Hallucination | 🔴 Hallucination | Both articles 1106-73-08 and 1106-43-08 are rated for the same working pressure: 47.0 MPa. |
| 28 | Between 1106-73-16 and 1106-43-16, which one has a larger bending radius? | 310 mm | 🟡 Partial Answer | 🔴 Hallucination | Neither; both article 1106-73-16 and 1106-43-16 have the same bending radius: 310 mm. |
| 29 | I need the internal diameter (mm) and working pressure (MPa) for article 1110-00-04. | 6.5 mm; 10.0 MPa | 🟢 Correct | 🔴 Hallucination | Article 1110-00-04 has an internal diameter of 6.5 mm and a working pressure rating of 10.0 MPa. |
| 30 | What is the documented weight for article 1110-00-08? | 0.27 kg/m | 🟢 Correct | 🟡 Partial Answer | The unit weight specified for article 1110-00-08 is 0.27 kg/m. |
| 31 | Can you find the mechanical bending radius for the 1110-03-06 hose? | 40 mm | 🟢 Correct | 🔴 Hallucination | The specified (mechanical) bending radius for article 1110-03-06 is 40 mm. |
| 32 | Compare the internal diameters of 1110-00-06 and 1110-03-06. Are they identical? | 10.0 mm | 🟢 Correct | 🟡 Partial Answer | Both article 1110-00-06 and 1110-03-06 have the same internal diameter: 10.0 mm. |
| 33 | What's the performance rating for working pressure on the 1101-00-03? | 25.0 MPa | 🟢 Correct | 🟡 Partial Answer | The Hydroscand documentation rates article 1101-00-03 for a working pressure of 25.0 MPa. |
| 34 | Is there a maximum length limit for article 1101-14-04-30 on a reel? | 260 | 🟢 Correct | 🟡 Partial Answer | Reel specifications for 1101-14-04-30 indicate a maximum reel length of 260. |
| 35 | We need to know the outer diameter (YD) for the 1101-14-12 hose. | 27.8 mm | 🔴 Hallucination | 🟢 Correct | The specified outer diameter (YD) for article 1101-14-12 is 27.8 mm. |
| 36 | How heavy is article 1101-14-20 per meter? | 1.23 kg/m | 🟢 Correct | 🟡 Partial Answer | Article 1101-14-20 has a documented unit weight of 1.23 kg/m. |
| 37 | Find the minimum allowed bend radius for the 1101-14-32 configuration. | 630 mm | 🟢 Correct | 🔴 Hallucination | The minimum allowed bend radius specified for article 1101-14-32 is 630 mm. |
| 38 | Can you specify the ID in inches for article 1101-14-24? | 1 1/2" | 🟢 Correct | 🟡 Partial Answer | The internal diameter for article 1101-14-24 is specified as 1 1/2 inch. |
| 39 | Which of the two, 1101-14-10 or 1101-14-16, is rated for higher working pressure? | 13.0 vs 8.8 MPa | 🟡 Partial Answer | 🟡 Partial Answer | Article 1101-14-10 is rated at 13.0 MPa and 1101-14-16 at 8.8 MPa; therefore, 1101-14-10 has the higher working pressure. |
| 40 | Verify the working pressure rating for article 1071-00-04. | 22.5 MPa | 🟢 Correct | 🟡 Partial Answer | The working pressure for article 1071-00-04 is 22.5 MPa. |
| 41 | What is the outer diameter specification for the 1071-00-12 hose? | 27.7 mm | ⚪ Parser Error | 🔴 Hallucination | The catalogue specifies an outer diameter (YD) of 27.7 mm for article 1071-00-12. |
| 42 | I need the unit weight for article 1071-00-16. | 0.88 kg/m | 🟢 Correct | 🔴 Hallucination | Article 1071-00-16 has a specified unit weight of 0.88 kg/m. |
| 43 | Compare the bend radii of 1071-00-24 and 1071-00-32. Which is more flexible? | 500 vs 630 mm | 🟡 Partial Answer | 🔴 Hallucination | Article 1071-00-24 has a bend radius of 500 mm and 1071-00-32 has 630 mm; therefore, 1071-00-24 is more flexible. |
| 44 | Determine the weight per meter for article 1003-11-04. | 22 kg/m | 🟢 Correct | 🔴 Hallucination | According to the technical data, article 1003-11-04 has a unit weight of 22 kg/m. |
| 45 | What is the internal diameter (ID mm) of the 1003-11-12 hose? | 19 mm | 🟢 Correct | 🟢 Correct | The Hydroscand record for article 1003-11-12 specifies an internal diameter of 19 mm. |
| 46 | Between 1003-11-06 and 1003-11-16, which one can handle more pressure? | 18 vs 8.8 MPa | 🟡 Partial Answer | 🔴 Hallucination | Article 1003-11-06 is rated for 18 MPa, while 1003-11-16 is rated for 8.8 MPa; therefore, 1003-11-06 can handle more pressure. |
| 47 | What is the mechanical bend radius for article 1003-11-12? | 240 mm | 🟢 Correct | 🟡 Partial Answer | The documented mechanical bend radius for article 1003-11-12 is 240 mm. |
| 48 | Can you provide the outer diameter (YD) for article 1102-14-04? | 14.04 mm | 🟢 Correct | 🟡 Partial Answer | For article 1102-14-04, the specified outer diameter (YD) is 14.04 mm. |
| 49 | What is the longest bobbin length we can order for 1102-14-08-30? | 95 | 🟢 Correct | 🟡 Partial Answer | The bobbin configuration 1102-14-08-30 has a documented maximum bobbin length of 95. |
| 50 | Compare the weight of 1102-14-04 and 1103-03-04. Are there significant differences? | 0.31 vs 0.18 kg/m | 🟡 Partial Answer | 🟡 Partial Answer | Article 1102-14-04 is 0.31 kg/m and 1103-03-04 is 0.18 kg/m; therefore, 1102-14-04 is heavier and the difference is noticeable. |

---

## Appendix C: Annotated Query Sets

### C.1 Case I — Hydroscand (*n* = 10 of 40 shown)

| Q# | Query | Ground Truth | Error Class |
|----|-------|--------------|-------------|
| Q63 | What is the maximum temperature for hose 1071-00-16? | +150 °C (HYDROSCAND HI-TEMP, verified p. 47 of catalogue). | Correct (single-cell lookup). |
| Q37 | How many millimetres is 1/8 inch? | 3.175 mm (conversion table, chapter 11). | Correct (trivial arithmetic). |
| Q46 | What is the ISO standard for textile hose protection? | ISO 6945 (abrasion resistance); pressure test per SAE J343. | Correct. |
| Q64 | Which sleeve fits hose 1118-12-16? | Sleeve 4200-19-16 (compact 4-spiral, 1"). | Hallucination — cited 4200-20-xx (wrong spiral count). |
| Q65 | What is the burst pressure for 1105-10-08? | 180 MPa (table p. 17). | Hallucination — returned working pressure instead of burst. |
| Q70 | How do I calculate hose length under dynamic load? | Multiply static length by elongation factor (1.02–1.04) under rated pressure. | Partial — omitted factor values. |
| Q45 | How much heavier is 1103-03-16 than 1103-03-04? | 0.64 kg/m (0.82 vs 0.18). | Parser error — returned individual values but no subtraction. |
| Q49 | Which article number has the highest working pressure in the 1106-73 series? | All rated 47 MPa (equal). | Partial — returned first match only. |
| Q66 | What does the 'P' designation mean in product codes? | Permanent coupling (crimped or swaged). | Hallucination — fabricated definition. |
| Q42 | Can I run refrigerant R134a through 1110-03-06? | No; not listed in chemical compatibility table (p. 93). | Partial — did not reference the table or provide rationale. |

### C.2 Case II — SAAB (*n* = 10 of 38 shown)

| Q# | Query | Ground Truth | Error Class |
|----|-------|--------------|-------------|
| Q12 | What is the shell size for connector P/N ABC-1234-56? | Size 16 (Doc D-789, Table 3.2, col. 4). | Correct (single-table lookup). |
| Q03 | How many contacts does the XYZ-7890 receptacle have? | 37 contacts (Doc D-456, Table 2.1). | Correct. |
| Q18 | Which document revision supersedes D-123 rev. A? | D-123 rev. B (issued 2023-11-02). | Correct (revision-control lookup). |
| Q07 | What is the recommended torque for contact retention? | 0.5–0.6 Nm (Doc D-789, section 4.3). | Hallucination — cited incorrect document. |
| Q22 | Can the connector handle 150 °C continuous operation? | No; max rated 125 °C (Doc D-012, Table 5). | Hallucination — answered "Yes" without temperature check. |
| Q11 | What cable diameter range fits shell size 20? | 12.0–16.5 mm (Doc D-456, Table 3.1, col. 3). | Parser error — returned unformatted text instead of range. |
| Q29 | How do I distinguish plug from receptacle by P/N? | Last digit: 1 = plug, 2 = receptacle (Doc D-789, Appendix C). | Partial — omitted reference to appendix. |
| Q14 | Are contact inserts interchangeable between revisions? | No; geometric tolerance updated in rev. C. | Hallucination — claimed "Yes" without checking revision notes. |
| Q05 | What is the minimum insertion/extraction cycle count? | 500 cycles (Doc D-012, section 6.2). | Partial — returned value but omitted source section. |
| Q31 | Which materials meet MIL-STD-1553 screening? | Nickel-plated beryllium copper (Doc D-345, Table 7). | Hallucination — fabricated material specification. |

---

## Appendix D: Detailed Execution Traces

This appendix provides complete parameter and output records for the worked examples presented in Sections 4.1 (Case I) and 4.2 (Case II). These tables demonstrate how each function invocation materializes concrete artifacts in `FunctionOutputInSession` and `FunctionParametersInSession`, enabling fine-grained inspection, replay, and failure attribution at record level.

### D.1 Case I: Hydroscand Product Catalogue

Tables D.1 and D.2 show the complete execution trace for the specification lookup query: *"Vilken gängstorlek har en 4201-16-16?"* (Section 4.1).

**Table D.1 — Function Output in Session, Case I (abridged)**

*Note: OID = Output ID, FID = Function ID. Grouped rows indicate outputs for the same function call.*

| OID | FID | Function Name | Output Name | Output Value | Type |
|-----|-----|---------------|-------------|--------------|------|
| 1 | 1 | Extract Product Code | `keyword_output` | `4201-16-16` | string |
| 2 | 2 | Query Database | `items` | `[{product_id: 685, product_code: 4201-16-16, …}, {product_id: 712, …}]` | json |
| 3 | 2 | Query Database | `count` | `2` | integer |
| 4 | 2 | Query Database | `result_source` | `products` | string |
| 5 | 3 | Extract Attributes | `extracted_data` | `[{product_code: 4201-16-16, specifications: {Gänga: G 1"}, …}]` | json |
| 8 | 4 | Analyze with LLM | `analysis` | `Gängstorleken för 4201-16-16 är G 1".` | string |

**Table D.2 — Function Parameters in Session, Case I (abridged)**

*Note: PID = Parameter ID, FID = Function ID. Grouped rows indicate parameters for the same function call.*

| PID | FID | Function Name | Parameter Name | Parameter Value | Type |
|-----|-----|---------------|----------------|-----------------|------|
| 1 | 1 | Extract Product Code | `input` | `Vilken gängstorlek har en 4201-16-16?` | string |
| 2 | 2 | Query Database | `query_type` | `select` | string |
| 3 | 2 | Query Database | `table` | `products` | string |
| 4 | 2 | Query Database | `keyword_output` | `4201-16-16` | string |
| 8 | 2 | Query Database | `limit` | `100` | integer |
| 10 | 3 | Extract Attributes | `items` | `[{product_id: 685, product_code: 4201-16-16, …}]` | json |
| 13 | 4 | Analyze with LLM | `task` | `advice` | string |
| 16 | 4 | Analyze with LLM | `question` | `Vilken gängstorlek har en 4201-16-16?` | string |

### D.2 Case II: SAAB Aerospace Documentation

Tables D.3 and D.4 show the execution trace for the *Simple Lookup* strategy applied to revision-controlled technical documentation (Section 4.2).

**Table D.3 — FunctionOutputInSession, Case II (abridged)**

| OID | FID | Function Name | Output Name | Output Value | Type |
|-----|-----|---------------|-------------|--------------|------|
| 1 | 1 | Extract product code | `identifier` | `COMP_[ID-01]` | string |
| 2 | 2 | Find latest document | `document_id` | `DOC_[D12]` | string |
| 3 | 3 | Table search | `count` | `2` | integer |
| 4 | 4 | Filter table | `filtered_rows` | `[ROW_01, …]` | json |
| 5 | 5 | Assemble table | `table_artifact` | `{fields: …}` | json |
| 6 | 6 | Analyse with LLM | `analysis` | `"Attribute X is …"` | string |

**Table D.4 — FunctionParametersInSession, Case II (abridged)**

| PID | FID | Function Name | Parameter Name | Parameter Value | Type |
|-----|-----|---------------|----------------|-----------------|------|
| 1 | 1 | Extract product code | `input_query` | `"Query_[Q01]"` | string |
| 2 | 2 | Find latest document | `candidate_docs` | `[DOC_A, …]` | json |
| 3 | 3 | Table search | `document_id` | `DOC_[D12]` | string |
| 4 | 4 | Filter table | `ruleset` | `RULE_[R01]` | string |
| 5 | 6 | Analyse with LLM | `assembled_data` | `{table: …}` | json |
