# Peer Review Critique
## "A Domain-Agnostic Agentic Architecture for Structured Extraction of Engineering Knowledge"
**Target venue:** Applied Artificial Intelligence, Taylor & Francis (Q2, IF 4.3)

---

## Journal Fit

The paper is well-suited to AAI's scope — applied AI for engineering, comparative evaluation of AI systems, and practical frameworks for industry. The topic is timely. That said, AAI reviewers at this impact factor tier will expect a complete, rigorous, and internally consistent empirical section, which is currently the paper's most serious weakness. Average time to publication is ~46 weeks; submitting prematurely risks desk rejection before peer review even begins.

---

## I. Critical — Likely Rejection Without Resolution

### C1. The evaluation is explicitly incomplete and must not be submitted in its current state
- [ ] Two tables in Section 5 carry the annotation *"TABLE NOT FINALIZED — REMAKING EVALUATION."*
- No journal at Q2 level will consider a manuscript with self-declared unfinished empirical results.
- This is a submission-blocking problem. The entire evaluation must be completed, re-run, and re-reported before submission.

---

### C2. The core results contradict the paper's central claims
The abstract states the architecture "reduces unsupported generations" and "improves citation and revision fidelity." The evaluation table directly contradicts both:

| Metric | RAG | RCP (Proposed) | Direction |
|--------|-----|----------------|-----------|
| Hallucination Rate | 22.0% | 24.5% | ❌ RCP is **worse** |
| Citation Accuracy | 48.0% | 32.7% | ❌ RCP is **worse** (−15 pts) |
| Unit Fidelity | 78.0% | 73.5% | ❌ RCP is **worse** |
| Answer Correctness | 50.0% | 59.2% | ✅ RCP is better (+9 pts) |

- [ ] If these numbers are incorrect (likely, given the "not finalized" note), fix them and update the abstract accordingly.
- [ ] If these numbers are correct after re-evaluation, the framing and abstract must change to reflect what the results *actually* show.
- The discussion does not adequately reconcile these contradictions.

---

### C3. The Agentic (No RCP) baseline appears to be a strawman
- A 10% accuracy / 42% hallucination rate for a baseline using the same corpus and tool set is implausibly poor.
- [ ] Justify the 5-iteration cap: why was this ceiling chosen?
- [ ] Show that a well-configured non-persistent agent with more iterations cannot match RCP performance.
- [ ] Either strengthen the baseline description or more generously configure the opponent system.

---

### C4. No statistical significance testing
- With N = 40 queries, a 9-point correctness difference between RAG and RCP could plausibly be within random variation.
- [ ] Add McNemar's test (appropriate for binary correctness scores) for all pairwise comparisons.
- [ ] Add confidence intervals or bootstrap resampling for all reported percentages.
- This is expected at Q2 level with an IF of 4.3.

---

## II. Significant — Will Likely Trigger Major Revision

### S1. Evaluation covers only one case study quantitatively
- [ ] All metrics in Section 5.2 refer exclusively to Case I (Hydroscand). Case II has no reported correctness, hallucination, or citation figures.
- Both cases are presented as joint evidence for generality; both must be evaluated quantitatively.
- As written, Case II functions as a qualitative illustration rather than a controlled evaluation.

---

### S2. The "domain-agnostic" claim is not validated
- Both cases are engineering/manufacturing documentation, same country, same problem class (structured product/technical data retrieval), same modalities (tables, text, PDFs).
- [ ] Either validate on at least one meaningfully different domain (legal, medical, financial), or revise the "domain-agnostic" claim in the title and abstract to "domain-adaptable" or "engineering-document-general."

---

### S3. The LLM choice undermines reproducibility and generalizability
- `Llama3.2:latest` via Ollama is not a fixed version — "latest" changes over time.
- [ ] Pin the exact model version (e.g., `llama3.2:3b`) for reproducibility.
- [ ] Add a note or sensitivity analysis discussing how results might differ with stronger models (GPT-4o, Claude 3.5, etc.).
- Results from a weak local model may not reflect architectural capability, and reviewers will ask whether the performance differences are architectural or just an artifact of the LLM's limitations.

---

### S4. The abstract directly contradicts the results
- [ ] The abstract claims "improved citation and revision fidelity." Citation accuracy is *lower* for RCP than RAG in the current data — this sentence is factually wrong.
- [ ] Once the evaluation is finalized, rewrite the abstract to accurately reflect what the results show.

---

### S5. Inconsistency in query set size
The paper gives three different numbers in three places with no reconciliation:

| Location | N stated |
|----------|----------|
| Section 5.1 ("annotated query set") | 50 |
| Section 5.2.1 ("human-annotated engineering queries") | 40 |
| Appendix B (actual queries listed) | 50 |

- [ ] Decide on one number and use it consistently.
- [ ] If 10 queries were excluded, state why explicitly.

---

### S6. Section 3.6 is incomplete (leftover `\textcolor{red}{}` marker)
- In the original LaTeX, Section 3.6 heading is flagged `\textcolor{red}{}` — indicating a draft section.
- The computational characteristics and limitations subsections are entirely commented out.
- [ ] Restore, complete, and integrate the time/space complexity analysis (`O(S·P)` strategy selection, `O(log N)` to `O(N)` retrieval, etc.).
- [ ] Restore the formal limitations subsection (noted as "future work" in the commented-out text).
- Reviewers evaluating an architecture paper will expect this analysis.

---

### S7. AI tool disclosure does not comply with Taylor & Francis policy
- The Acknowledgements state the authors used **"ChatGPT-5"** — this model name does not exist publicly.
- T&F policy requires disclosure of the **exact tool name, version, and purpose** of any generative AI used.
- [ ] Correct to the actual model used (e.g., "ChatGPT (GPT-4o, OpenAI, 2024)") with version and purpose stated.
- An incorrect tool name may trigger an editorial flag before peer review.

---

## III. Moderate — Would Weaken the Paper if Unaddressed

### M1. No ablation study
- The six-stage loop is the core architectural contribution, but no experiment isolates the value of individual stages.
- [ ] Run ablations: What happens if Stage 4 (function validation) is removed? Does Stage 5 (strategy validation) add value beyond Stage 4?
- [ ] Without ablation, reviewers cannot assess which design decisions are load-bearing.

---

### M2. Differentiation from existing workflow orchestration systems is insufficient
- The paper positions against "standard LangGraph deployments" but does not engage with the broader space of SQL-backed persistent orchestration systems:
  - Apache Airflow with LLM integrations
  - LlamaIndex workflows with persistence layers
  - CrewAI with memory
  - LangChain + SQLAlchemy with checkpointers
- [ ] Add a dedicated comparison paragraph (or table) in Related Work addressing why the RCP provides capabilities that these systems cannot.

---

### M3. "Domain-agnostic" title conflicts with hand-crafted domain-specific strategy libraries
- The paper acknowledges that "strategy templates are currently hand-crafted for each domain."
- A domain-agnostic *architecture* requiring significant domain-specific engineering effort is more accurately described as **domain-adaptable**.
- [ ] Either: (a) rename the claim to "domain-adaptable," or (b) demonstrate that strategy templates transfer across domains with minimal modification.

---

### M4. The RCP schema is described but never formally specified
- Section 3.2 describes design-time/run-time separation at length but provides no entity-relationship (ER) diagram or schema specification.
- [ ] Add a formal schema diagram (even simplified) showing tables, columns, types, and foreign key relationships.
- This is necessary for anyone attempting to replicate the architecture.

---

### M5. Temporary database lifecycle is underspecified
- Section 3.1 states the temporary database is "strictly short-lived" but does not answer:
  - When exactly is it destroyed?
  - Is any of its content transferred to the RCP before destruction?
  - How does deterministic replay work if the temporary database no longer exists?
- [ ] Resolve this apparent tension between the temporary DB's existence and the RCP's replay guarantee.

---

### M6. Error taxonomy is inconsistent with the quantitative table
- The error taxonomy in Section 5.3 covers: Hallucination, Partial Answer, Field-Name Mismatch.
- "Field-Name Mismatch" does not appear in the performance table (Table 5.2.1).
- "Parser Error" appears in the appendix tables but not in the Section 5.3 taxonomy.
- [ ] Make the error taxonomy exhaustive and consistent with both the quantitative table and the appendix.

---

### M7. Difficulty tiers are defined but never used analytically
- Section 5.3 defines Easy/Medium/Hard tiers — which is valuable — but results are never broken down by tier.
- [ ] Add tier-stratified results: Do RCP's gains concentrate in Hard queries? Does RAG outperform RCP on Easy lookups?
- This would make the contribution significantly more precise and convincing.

---

## IV. Minor — Presentation, Compliance, and Style

### P1. Case II has no quantitative results despite being in the evaluation section
- [ ] Section 5 claims evaluation on "two industrial case studies" but only reports numbers for one. Either restrict the claim to Case I or add Case II figures.

---

### P2. Inconsistent use of "agent," "function," and "tool"
- Section 4.2 defines: *agent* = orchestrating entity, *function* = atomic executable operation.
- But Section 3 and Algorithm 1 use "agent execution" and "agent calls" to describe what are later called functions.
- [ ] Define terms up-front in a glossary or in Section 3 and apply them consistently throughout.

---

### P3. `func_analyse_data` footnote is an awkward workaround
- A footnote bridges "Analyse With LLM" (used in tables) and `func_analyse_data` (callable identifier).
- This reflects a naming inconsistency in the system itself.
- [ ] Use the callable identifier consistently in all tables and explain the naming convention once in prose, eliminating the need for a footnote.

---

### P4. Remove all `\textcolor{red}{}` markers before submission
- [ ] Section 3.6 heading still carries a red-color markup from the draft.
- Leftover LaTeX formatting artefacts signal an unpolished draft to editors and reviewers.

---

### P5. Verify public GitHub repositories before submission
- The Data Availability Statement references two GitHub repos.
- [ ] Verify that both `oscik559/Hydroscand_Produktbok` and `oscik559/Project_Saab` are publicly accessible and contain the described code. Reviewers may check these.

---

### P6. Latency figure discrepancy
- Operational cost table (Section 5.2.2): Agentic (No RCP) baseline = **4.03s**
- Section 5.3 prose: same baseline = **3.59s**
- [ ] Reconcile these two numbers — one of them is wrong.

---

### P7. Case II is missing Layer 3 (application-level interaction)
- Case I has three layers: extraction → agentic reasoning → application-level interaction.
- Case II describes only two (extraction and agentic reasoning).
- [ ] Either add a Layer 3 description for Case II or explicitly note that it was not implemented and explain why.

---

## Summary Scorecard

| Dimension | Assessment | Priority |
|---|---|---|
| Conceptual originality | ✅ Strong — RCP as relational orchestration layer is a genuinely useful framing | — |
| Industrial relevance | ✅ Strong — two real partners, real documents | — |
| Related work | ⚠️ Adequate, but missing workflow orchestration comparison | M2 |
| Methodology / architecture | ⚠️ Well-designed control loop, but evaluation design is weak | C3, C4 |
| Evaluation completeness | ❌ Critical failure — tables unfinished, results contradictory, single-case quantitative | C1, C2, S1 |
| Statistical rigor | ❌ Absent — no significance testing | C4 |
| Reproducibility | ⚠️ Partial — code public, but LLM version unpinned, temp DB lifecycle unclear | S3, M5 |
| Writing / consistency | ⚠️ Good overall, terminology inconsistencies | P2, P3 |
| T&F compliance | ⚠️ Needs correction — AI disclosure has incorrect model name | S7 |

---

## Recommended Submission Checklist

Work through these in order before submitting:

- [ ] **C1** — Complete both evaluation tables with final numbers
- [ ] **C2 / S4** — Reconcile results with abstract and contribution claims
- [ ] **C3** — Strengthen or replace the Agentic (No RCP) baseline
- [ ] **C4** — Add McNemar's test and confidence intervals
- [ ] **S1** — Add quantitative results for Case II
- [ ] **S2** — Revise "domain-agnostic" claim or add a third domain
- [ ] **S3** — Pin exact LLM version; add model sensitivity note
- [ ] **S5** — Fix query count inconsistency (50 vs 40)
- [ ] **S6** — Restore Section 3.6 complexity and limitations content
- [ ] **S7** — Fix AI tool disclosure (correct model name and version)
- [ ] **M1** — Add ablation study for the six-stage loop
- [ ] **M2** — Add comparison with LangChain/LlamaIndex/Airflow in Related Work
- [ ] **M4** — Add formal RCP schema diagram
- [ ] **M5** — Clarify temporary database lifecycle and replay mechanism
- [ ] **M6** — Make error taxonomy consistent with quantitative tables
- [ ] **M7** — Add tier-stratified (Easy/Medium/Hard) results breakdown
- [ ] **P6** — Fix latency discrepancy (4.03s vs 3.59s)
- [ ] **P7** — Add Case II Layer 3, or note its absence explicitly
- [ ] **P4** — Remove all `\textcolor{red}{}` draft markers from LaTeX
- [ ] **P5** — Verify both GitHub repos are public and contain correct code
