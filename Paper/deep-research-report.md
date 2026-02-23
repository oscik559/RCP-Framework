# Peer-review report on A Domain-Agnostic Agentic Architecture for Structured Extraction of Engineering Knowledge

## Executive summary

This manuscript proposes a validation-centric “agentic” architecture for extracting engineering facts from heterogeneous technical documentation, especially where table fidelity, revision scope, and audit-ready provenance are required. The core technical idea is a persistent SQL-backed **Relational Control Plane (RCP)** that stores goals, strategies, agent/tool calls, intermediate artefacts, and validation outcomes as first-class relational entities, with reasoning governed by a six-stage control loop that enforces evidence gating before final answers are emitted. fileciteturn0file0

The problem framing is timely and practically important: engineering documentation is often table-dense, multimodal, multilingual, and revision-controlled, and many deployment failures of retrieval-augmented generation (RAG) and ad‑hoc agent pipelines stem from hallucinations, weak validation, and weak traceability. fileciteturn0file0 citeturn11search3turn7search0

The main barrier to acceptance in its current form is **evidentiary** rather than conceptual. The paper defines evaluation metrics and baselines but (in the provided manuscript version) largely reports *worked examples and architectural traces* rather than *quantitative results* (e.g., accuracy, citation correctness, unit/revision fidelity, hallucination rate, cost). Consequently, several strong claims in the abstract and discussion (“improves… reduces…”) are not fully supported by presented evidence. fileciteturn0file0

A second barrier is **reproducibility and artefact verification**. The manuscript states that implementation code is available at two GitHub repositories, but both URLs presented in the paper are not accessible (HTTP 404) at the time of this review; additionally, the underlying industrial data are not publicly available due to confidentiality. Together, these substantially reduce independent verifiability, and they heighten the need for a public benchmark slice (e.g., on fully public corpora) and a detailed reproducibility appendix. fileciteturn0file0 citeturn4view0turn4view1

### Concise evaluation checklist

| Criterion | Assessment | Evidence / rationale |
|---|---|---|
| Problem importance and motivation | Strong | Clear articulation of failure modes in engineering RAG/agents (tables, revisions, provenance). fileciteturn0file0 |
| Conceptual contribution (RCP + gated loop) | Strong–Moderate | Treating orchestration as persistent, queryable data is compelling; needs sharper novelty boundary vs existing persistence/observability tooling. fileciteturn0file0 citeturn6search0turn6search12 |
| Methodological transparency | Moderate–Weak | Architecture is described in detail, but critical implementation factors are underspecified (models, prompts, extraction tools, corpus/query sizes). fileciteturn0file0 |
| Evaluation design & controls | Moderate–Weak | Baselines and metrics are defined, but quantitative outcomes and fairness controls are not clearly reported in the current version. fileciteturn0file0 |
| Statistical rigour | Weak | No confidence intervals, effect sizes, significance tests, or power discussion; unclear sample sizes. fileciteturn0file0 |
| Reproducibility & artefacts | Weak | Data restricted; stated code URLs not accessible; lacking environment + versioning details required for deterministic replay. fileciteturn0file0 citeturn4view0turn4view1 |
| Writing and presentation quality | Moderate | Generally readable, but placeholders and internal inconsistencies (e.g., captions, section references, table mismatches). fileciteturn0file0 |
| Ethics, governance, and operational risk awareness | Moderate | Mentions confidentiality and disclosure; stronger security/privacy and retention analysis is needed given persistent trace storage. fileciteturn0file0 |

## Bibliographic metadata and context

**Manuscript identity and authorship.** The provided document is titled *“A Domain-Agnostic Agentic Architecture for Structured Extraction of Engineering Knowledge”* and lists four authors: entity["people","Mehdi Tarkian","liu faculty member"], entity["people","Oscar Ikechukwu","liu researcher"], entity["people","Sanjay Nambiar","liu researcher"], and entity["people","Marie Jonsson","liu faculty member"]. The single affiliation given is the Division of Product Realization, Department of Management and Engineering at entity["organization","Linköping University","university in sweden"] (Linköping, Sweden). fileciteturn0file0

**Date and venue.** The manuscript shows “ARTICLE HISTORY: Compiled February 23, 2026”, which appears to be a build/compile date rather than a publication date. No DOI and no explicit journal/conference venue are stated in the header; however, the methods section references an “Applied Artificial Intelligence emphasis on comparative evaluation,” suggesting (but not confirming) a targeted venue or style. fileciteturn0file0

**Funding and acknowledgements.** Funding is attributed to entity["organization","Vinnova","swedish innovation agency"] under grant “2024-01420 – Data Automation and Retrieval Technology (DART)”. fileciteturn0file0 A publicly available programme page for DART describes it as addressing industrial challenges in managing heterogeneous data formats and mentions the use of RAG for data analysis and management, which aligns well with the manuscript’s industrial motivation. citeturn1search1

**Disclosure and AI-assistance statement.** The paper contains a competing-interests statement (“no competing interests”) and a disclosure that “ChatGPT-5 was used… solely to assist with editing and language refinement,” with human review asserted. fileciteturn0file0

**Citation count and indexing.** Citation count is not provided in the manuscript and could not be reliably verified from the information available here; the document appears to be a working manuscript rather than a clearly indexed preprint/publication. fileciteturn0file0

## Aims, hypotheses, and main claims

**Stated aim.** The paper aims to make LLM-based extraction from engineering documentation more trustworthy by enforcing evidence-centric progression, validation gates, and audit-ready provenance—particularly for tables and revision-controlled documentation. fileciteturn0file0

**Hypotheses.** The paper does not state formal hypotheses in the statistical sense. Instead, it advances a set of engineering claims that can be reframed as testable hypotheses:

- Persisting orchestration artefacts in a relational schema (RCP) improves observability, replayability, and governance relative to transient in-memory agent state. fileciteturn0file0  
- A six-stage goal–strategy–agent–validation loop reduces unsupported generations and improves citation/revision fidelity compared to baseline RAG and unvalidated agent pipelines. fileciteturn0file0  
- The architecture is “domain-agnostic” insofar as it can be re-instantiated across engineering document domains by swapping strategy/agent libraries without architectural modification. fileciteturn0file0

**Main contributions (as claimed).** The paper enumerates three contributions: (i) a validation-centric six-stage control loop; (ii) the SQL-backed RCP persisting goals/strategies/function calls/validations; and (iii) evaluation on two industrial case studies with baseline comparisons and operational metrics (latency/cost). fileciteturn0file0

**Key claims that require stronger substantiation in the current version.** In the abstract and discussion, the manuscript claims improvements in citation and revision fidelity, reductions in unsupported generation, and transparent queryable traces. These are plausible outcomes of the proposed design, but the current manuscript text (as provided) does not show the quantitative evidence needed to validate “improves/reduces” claims robustly. fileciteturn0file0

## Methodology, evaluation design, and statistical rigour

### Architectural design and methodological clarity

**Six-stage control loop.** The controller is described as executing a six-stage loop: goal definition (with explicit success criteria), strategy selection, agent execution, agent validation, strategy validation, and goal validation. The manuscript positions this as a governance mechanism that prevents “generate-then-justify” behaviour by requiring validation to pass at multiple levels before finalisation. fileciteturn0file0

**Relational persistence model (RCP).** The central methodology is not a new retrieval model but an orchestration substrate: all run-time artefacts are stored in SQL tables (goal/strategy instances, function invocations, parameters, outputs, validation results). The paper argues this enables deterministic replay and auditable provenance using standard database queries rather than bespoke logs. fileciteturn0file0

**Study-flow visualisation.** The paper includes a flow diagram showing the loop and its interactions with a “harvested database,” a “temporary database,” and an “agentic database” (RCP). The diagram is helpful conceptually but includes placeholder caption text (“Enter Caption”), which undermines presentation quality and suggests a draft state. fileciteturn0file0

A mermaid schematic consistent with the manuscript’s description (not a reproduction of their figure) is:

```mermaid
flowchart TD
  U[User query] --> G[Goal definition\n(success criteria, revision scope,\nrequired evidence granularity)]
  G --> S[Strategy selection\n(template plan + sufficiency condition)]
  S --> E[Agent execution\n(tool calls / functions)]
  E --> AV{Agent validation\n(schema, units, anchors, plausibility)}
  AV -- pass --> SV{Strategy validation\n(sufficiency met? conflicts resolved?)}
  AV -- fail --> E
  SV -- pass --> GV{Goal validation\n(acceptance predicate)}
  SV -- fail --> S
  GV -- pass --> R[Final answer\nwith provenance]
  GV -- fail --> G

  H[(Harvested DB:\nobjectified engineering knowledge)] -. evidence .-> E
  T[(Temporary DB:\nsession-scoped intermediates)] -. intermediates .-> E
  RCP[(Relational Control Plane:\ngoals, calls, artefacts, validations)] --- G
  RCP --- S
  RCP --- E
  RCP --- AV
  RCP --- SV
  RCP --- GV
```

### Evaluation design, baselines, and threats to validity

**Declared baselines and metrics.** The paper states two baselines: (i) standard RAG (retrieve top‑k chunks then generate), and (ii) an agentic tool-use pipeline without the RCP persistence model and without validation gates. It defines metrics including answer correctness against an annotated query set, citation accuracy, unit fidelity, revision/applicability fidelity, hallucination rate (unsupported factual claims), and operational cost (latency and token/compute budget). fileciteturn0file0

**Critical missing elements (as presented).** The manuscript describes what will be measured but does not clearly report (in the provided text) the necessary quantitative evaluation artefacts:

- Corpus scale descriptors (pages/tables, multilinguality, revision counts) are referenced as something the authors intend to report, but the actual numbers are not plainly stated. fileciteturn0file0  
- The evaluation query set size, composition, sampling procedure, and annotation guidelines are not included in a form that would allow assessment of statistical reliability or selection bias. fileciteturn0file0  
- Results that directly compare proposed vs baselines on the defined metrics are not presented as tables/plots with confidence intervals or tests. fileciteturn0file0

**Case-study methodology.** The evaluation is framed as two industrial case studies:

- A hydraulic product catalogue use case, linked to a public “Produktbok” catalogue for which the paper discusses Swedish-language text, dense tables, unit conventions, and thread standards. fileciteturn0file0 citeturn3search0turn15search9  
- A revision-controlled engineering documentation use case in collaboration with entity["company","Saab","defense and aerospace, sweden"], with proprietary identifiers and content masked due to confidentiality. The paper emphasises revision awareness and multimodal layouts. fileciteturn0file0 citeturn15search4  

These are credible industrial settings, but they introduce **two major validity risks**:

1. **Baseline fairness and confounding by upstream extraction.** The architecture includes a document “harvesting” stage that structures PDFs/tables into a normalised SQL database before agent reasoning. If baselines operate on less-structured representations (e.g., raw PDF chunks), then improvements may be driven by pre-processing and structured storage rather than by the RCP/validation loop per se. The manuscript needs an explicit fairness protocol showing what components are shared between systems and what differs. fileciteturn0file0  
2. **Generalisation and “domain-agnostic” scope.** Two engineering domains are helpful, but both remain within similar document genres (engineering artefacts, tables, revisions). The claim “domain-agnostic” should be bounded more carefully—e.g., “domain-agnostic within engineering document domains provided that harvesting/objectification adapters exist”—or expanded via additional public benchmarks. fileciteturn0file0  

### Statistical analyses, effect sizes, and power

**Stated vs executed statistical practice.** The manuscript does not report inferential statistics (tests, assumptions), effect sizes, or power analyses. In case-study evaluation of RAG/agents, some inferential machinery is still feasible and valuable:

- For binary correctness and citation fidelity, report proportions with confidence intervals (e.g., Wilson intervals) and paired tests if using the same query set across systems (e.g., McNemar’s test).  
- For continuous outcomes (latency, cost), report distributions, medians/IQR, and non-parametric paired tests if appropriate.  
- For annotation-based outcomes, report inter-annotator agreement and adjudication protocol.

Without these, “improves/reduces” statements are not well-supported in the scientific sense, even if engineering intuition suggests improvement. fileciteturn0file0

**How the assessment would change if missing details were supplied.** If the paper provided (i) a sizeable, clearly sampled query set; (ii) complete baseline parity; (iii) quantitative results with uncertainty; and (iv) ablations isolating RCP persistence vs validation vs harvesting, then the methodological evidence would likely rise from “case-study demonstration” to “comparative empirical evaluation” and the central claims would become much stronger. fileciteturn0file0

## Data, code, supplementary materials, and reproducibility checklist

### Data and supplementary materials

**Data access.** The paper states that supporting data are not publicly available due to confidentiality agreements with industrial partners, with possible release of anonymised artefacts/derived data upon reasonable request. fileciteturn0file0

This is common in industrial engineering research, but the architectural claims (especially about provenance, replay, and validation) are well-suited to **partial open release** strategies, such as:

- A fully public *open* case study using publicly accessible documents (e.g., the Hydroscand product catalogue pages already available online), with released query set, ground truth, and harvested database schema/data where licensing permits. citeturn3search0turn15search9  
- “Trace-only” releases that anonymise content but preserve structural properties: goal/strategy logs, validation outcomes, counts of retries, rates of failures, and timing/cost summaries—enough to reproduce *process* claims even if content cannot be shared.

### Code availability and verifiability

**Claimed availability.** The manuscript states that implementation code for the two case studies is available at two GitHub repositories. fileciteturn0file0

**Current verifiability issue.** Both repository URLs as written are not accessible (HTTP 404) at the time of review. This could reflect renaming, private visibility, or temporary removal, but from a reviewer’s perspective it means the “publicly available” claim is not currently verifiable and should be corrected (or the artefacts released) before publication. citeturn4view0turn4view1

### Reproducibility checklist

The manuscript strongly emphasises deterministic replay and governance, yet reproducibility in LLM systems is fragile unless model stochasticity and toolchain versions are tightly controlled. A minimum reproducibility bundle for this paper should align with widely used transparency norms (e.g., artefact availability expectations and reproducibility checklists). citeturn17search1turn17search0

A practical checklist tailored to this paper:

- **Environment and versions:** exact versions of the orchestration framework, database schema migrations, parsers/OCR tools, and LLM client libraries; OS/container recipe (Docker/Conda).  
- **Model details:** model names/versions, temperature/top‑p/seed settings, prompting templates, context window limits, and any caching strategy.  
- **Harvesting/objectification:** document corpus description (counts of PDFs/pages/tables; languages; scan quality), table extraction method, unit normalisation rules, and error-handling.  
- **Evaluation set:** query list, sampling method, annotation guidelines, adjudication process, and inter-annotator agreement.  
- **Baseline parity:** explicit statement of what each baseline shares (same harvested DB? same retriever? same evidence budget?) and what differs.  
- **Outcome reporting:** full metric tables, confidence intervals, and per-category breakdowns (tables vs text; Swedish vs English; revised vs single-rev docs).  
- **Security/privacy:** retention policy for traces, access controls, and redaction rules for stored artefacts (especially relevant in defence/industrial settings).

Where the paper currently stands: it provides a clear architectural description and includes worked examples of in-session tables and traces, but it does not yet provide the artefact bundle that would let third parties validate “deterministic replay” and “reduced hallucination” claims independently. fileciteturn0file0

## Literature context and novelty

### Positioning relative to core prior work

The manuscript’s framing (“RAG and agent pipelines fail due to hallucinations, weak validation, limited traceability”) aligns with broader findings that RAG can improve factuality but does not eliminate hallucinations and that additional grounding/verification mechanisms are needed. fileciteturn0file0 citeturn7search0turn11search3

Its emphasis on tables and PDFs is also well-motivated: table extraction and structure recognition remain challenging, motivating specialised datasets and tools (e.g., PubTables-1M for table extraction; GROBID for PDF-to-structured conversion; measurement extraction/normalisation via Grobid-quantities). fileciteturn0file0 citeturn11search0turn11search1turn13search14

The novelty claim rests less on “agents exist” (well-established via paradigms like ReAct and tool-use learning such as Toolformer) and more on **how orchestration and validation are operationalised as persistent relational data**. citeturn7search1turn7search2

### Comparison to five key prior works

| Citation | Main claim | Similarity / difference vs this paper | Methodological contrast |
|---|---|---|---|
| Lewis et al., 2020, *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* citeturn7search0 | Combine parametric LM with non-parametric retrieval memory to improve knowledge-intensive generation. | Similar: baseline “RAG-style” pipeline is one comparator; both care about provenance/knowledge access. Different: RAG is a model/pipeline approach, not a governance/persistence architecture. | Focuses on model formulation + benchmarks; does not define a persistent execution ledger with validation gates. |
| Yao et al., 2022, *ReAct: Synergizing Reasoning and Acting in Language Models* citeturn7search1 | Interleave reasoning traces and tool actions to improve task performance and interpretability. | Similar: motivates multi-step agentic tool use and reduced hallucination via external actions. Different: this paper formalises validation gating and SQL persistence of artefacts beyond textual “reasoning traces.” | ReAct primarily evaluates prompting trajectories; this paper proposes an external control plane with typed artefacts and validation predicates. |
| Sarthi et al., 2024, *RAPTOR* citeturn7search3 | Hierarchical summarisation + tree-organised retrieval improves long-document QA. | Similar: addresses long-document retrieval and coherence. Different: RAPTOR is retrieval representation; this paper is orchestration + governance across tools and modalities (tables/revisions). | RAPTOR’s evidence structure is retrieval-tree; this paper’s evidence structure is relational artefact storage and validation results. |
| LangGraph documentation (persistence/time-travel/checkpointers) citeturn6search0turn6search12 | Graph-based agent workflows with built-in persistence via checkpointers enabling resumption/time-travel and state access after execution. | Similar: both emphasise persistence, replay, and long-running agent workflows. Different: the manuscript’s RCP proposes a domain schema storing goals/strategies/contracts/validations, whereas LangGraph persistence focuses on graph state checkpoints. | LangGraph persists state snapshots; RCP persists *semantically typed* orchestration entities and validation outcomes designed for audit queries. |
| Kandasamy, 2025, *Control Plane as a Tool* citeturn8search0turn8search4 | “Control plane” pattern modularises tool orchestration for agentic systems to improve scalability/observability/safety. | Similar: conceptual convergence on a control-plane layer for orchestration and governance. Different: this manuscript implements a specific **relational** control plane with validation gates and domain strategy libraries, demonstrated in engineering case studies. | Kandasamy is primarily a design-pattern synthesis; this paper presents a concrete SQL schema + execution loop and (claimed) empirical case-study evaluation. |

### Novelty assessment

**What appears genuinely new (or at least well-integrated):**

- The explicit *goal → strategy → function → validation* decomposition persisted in relational form, with validation outcomes treated as first-class records and used to gate progression. fileciteturn0file0  
- The emphasis on audit-ready provenance at engineering-granularity (page/section/table cell), paired with revision/applicability fidelity as a first-class metric. fileciteturn0file0  

**Where novelty is currently underspecified:**

- Since LangGraph already provides persistence/checkpointing and “time travel” concepts, the paper must articulate precisely what capabilities are *not* available (or not practical) in existing persistence layers and why a bespoke relational schema materially changes outcomes. citeturn6search0turn6search12  
- The “domain-agnostic” claim requires either broader evaluation or clearer scoping to “multiple engineering documentation domains with reusable control-plane schema.” fileciteturn0file0  

## Strengths, weaknesses, potential biases, ethical concerns, and limitations

### Strengths

The manuscript offers a coherent architecture that directly targets real industrial failure modes: provenance, revision scope, unit normalisation, and table-grounded extraction. fileciteturn0file0 It also contributes a concrete “operationalisation” perspective: rather than proposing yet another retrieval method, it treats orchestration, validation, and traceability as the primary bottleneck in production-grade engineering knowledge systems. fileciteturn0file0

The worked examples and in-session tables demonstrate how such a system could support auditing and debugging by linking outputs to intermediate artefacts and validation checks. fileciteturn0file0

### Weaknesses and limitations

**Quantitative evidence gap.** The stated contribution includes baseline comparisons and metrics, but the provided manuscript text does not present the corresponding results in a way that allows independent assessment of improvement magnitude or statistical reliability. fileciteturn0file0

**Internal consistency and draft artefacts.** Several presentation issues undermine credibility and should be addressed prior to submission:

- Placeholder figure captions (“Enter Caption”) and section-number inconsistencies (e.g., referring to Strategy/Agent Library as “Section 3.2/3.3” while they appear earlier). fileciteturn0file0  
- Naming and tabular inconsistencies in the worked example: e.g., a function described as “Extract Product Number” appears labelled as a different function name in the table, and record counts appear inconsistent across tables. These may be simple editing errors, but they matter because the paper’s core contribution is *trace correctness*. fileciteturn0file0  

**Reproducibility and availability.** The code availability claim is presently unverifiable via the stated URLs, and the data are restricted. This combination makes the paper depend heavily on the completeness of prose reporting and on providing a public benchmark slice. fileciteturn0file0 citeturn4view0turn4view1

### Potential biases

- **Selection bias in queries and documents.** If the query set is constructed by system designers, it may over-represent “happy paths” and under-represent adversarial or ambiguous queries (e.g., conflicting revisions, malformed OCR tables). The paper mentions “annotated query set” but does not specify sampling and annotation independence. fileciteturn0file0  
- **Industrial confidentiality bias.** The SAAB case is necessarily masked; this limits community scrutiny and increases the need for a stronger public evaluation case (or synthetic surrogate corpora that preserve key properties). fileciteturn0file0  

### Ethical and security concerns

**Persistent trace storage can create sensitive-data risk.** The RCP is designed to persist “every intermediate artefact,” including retrieved passages and possibly proprietary document text, table cells, and tool outputs. In industrial contexts—especially defence-adjacent contexts—this raises concrete issues: access control, encryption at rest, retention/deletion policies, prompt-injection containment, and redaction of personally identifiable or export-controlled content. The paper gestures at governance but does not yet operationalise a security/privacy model. fileciteturn0file0

**AI-assisted writing disclosure is good practice.** The explicit disclosure about using ChatGPT for language refinement is a strength, and it aligns with evolving transparency expectations. fileciteturn0file0

## Recommendations for revision and further work, including title and abstract edits and a lay summary

### Highest-priority revisions for scientific rigour

**Add a results section with quantitative comparisons.** The paper already defines metrics and baselines; it should present a consolidated results table for each case study with:

- dataset descriptors (document counts, pages, tables, languages, revisions),  
- query set size and category breakdown,  
- metric values per system (proposed vs baseline RAG vs baseline non-validated agent),  
- uncertainty (confidence intervals) and (where appropriate) paired significance tests,  
- cost/latency distributions (median/IQR) rather than single-point numbers.

This single change would convert the strongest claims from plausible to verifiable. fileciteturn0file0

**Include ablations that isolate what improves what.** To establish that the *RCP + validation gates* are causal contributors (and not just the harvesting stage), add ablations such as:

- harvesting on/off (or same harvested DB for all systems),  
- validation gates on/off with identical tools,  
- persistence on/off with identical validation,  
- strategy-library complexity levels.

**Make baseline parity explicit.** A short table describing each system’s components (retriever, chunking, harvested DB usage, table parser, number of LLM calls, token budget) would address fairness concerns.

### Reproducibility and artefact recommendations

**Fix code availability and provide a reproducibility bundle.** If repositories are renamed or private, update the links and ensure long-term archival (e.g., tagged release + DOI via Zenodo). If industrial code cannot be fully released, publish a minimal reference implementation of the RCP schema and a runnable toy case with a public PDF corpus.

**Publish a public benchmark slice.** The Hydroscand catalogue is publicly accessible online; subject to licensing, consider publishing an *evaluation package* (queries + ground truth + extracted schema) that captures table/unit/revision issues. citeturn3search0turn15search9

**Adopt an artefact checklist.** Align supplementary materials with recognised reproducibility norms (e.g., artefact availability expectations and checklist structures). citeturn17search1turn17search0

### Engineering/practitioner guidance

For readers considering deployment, the paper would benefit from an explicit “when to use this” decision guide:

- appropriate domains (table-dense, revision-controlled, audit requirements),  
- cost trade-offs (storage overhead, validation latency),  
- operational hardening (redaction, access controls, monitoring),  
- how to evolve strategy libraries safely over time.

### Suggested title and abstract edits

**Suggested title (more specific, lower ambiguity).**  
*A Relational Control Plane for Validation-Gated Agentic Extraction from Engineering Documentation*

Rationale: foregrounds the actual novelty mechanism (relational control plane + validation gating) rather than the broad label “domain-agnostic,” which is hard to defend with two cases alone. fileciteturn0file0

**Abstract edits (substantive).** The current abstract contains strong comparative claims without presenting corresponding quantitative evidence in the manuscript. A revised abstract should either (i) add the headline numbers (with n of queries/documents) or (ii) soften claims to reflect qualitative findings until numbers are added. Concretely:

- Add corpus and evaluation sizes (“X documents, Y pages, Z queries per case study”).  
- Replace “improves… reduces…” with numeric deltas *or* with “we observe…” if still preliminary.  
- Specify the validation checks (schema completeness, unit normalisation, revision applicability, citation anchors) and clarify whether validation is rule-based, LLM-based, or hybrid. fileciteturn0file0

### Lay summary (≤150 words)

Engineers often need answers from manuals and catalogues that are not just plausible, but *verifiably correct*—including the right revision, the right units, and a citation to the exact table cell or clause. This paper proposes a system that organises an AI assistant’s work as a series of steps: defining what counts as success, selecting a plan, running specialised tools (e.g., table extraction), and validating each intermediate result before producing a final answer. Unlike many AI pipelines that keep their internal state in memory, this approach stores every step, tool call, output, and validation result in a structured SQL database, making the process auditable and repeatable. The authors illustrate the approach on two industrial document settings, aiming to reduce unsupported answers and improve traceability. fileciteturn0file0