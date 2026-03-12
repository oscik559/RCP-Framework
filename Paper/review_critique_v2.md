# Peer Review Critique — Version 2
## "A Domain-Agnostic Agentic Architecture for Structured Extraction of Engineering Knowledge"
**Target venue:** Applied Artificial Intelligence, Taylor & Francis (Q2, IF 4.3)
**Reviewed against:** `interactnlmsample__2_.tex`

---

## What Has Changed Since Version 1

The manuscript has been substantially revised and several previously critical issues are now resolved:

- ✅ **Evaluation is complete.** Both performance and operational cost tables are finalized with real numbers.
- ✅ **Three-tier ablation replaces the strawman baseline.** B2 (SQL-backed Retrieval, 82% correctness) is a credible and instructive intermediate step. The old "Agentic (No RCP)" baseline at 10% accuracy is gone.
- ✅ **Abstract now accurately reflects results.** Hallucination 48%→2%, correctness 52%→76% — these claims are now backed by the data.
- ✅ **Query count inconsistency resolved.** 50 queries used consistently.
- ✅ **Discussion of the B2→B3 correctness drop is well-reasoned.** The "verify-then-summarize" framing (explicit failure > silent misinformation) is intellectually sound and clearly explained.

These are significant improvements. The paper is now much closer to submission-ready.

---

## I. Critical — Must Resolve Before Submission

### C1. Case II has no quantitative results despite being framed as a full evaluation case
- [ ] Section 5 (Evaluation) reports numbers exclusively for Case I. Case II is described in qualitative detail in Section 4 but receives no rows in Table 5.1 or Table 5.2.
- The abstract and Introduction both claim "two industrial case studies." Reviewers evaluating a dual-case paper will expect dual-case metrics.
- **Options:** (a) Add Case II performance numbers to both tables, or (b) explicitly reframe Case II as a *qualitative demonstration* of generalizability rather than a formal evaluation, making that distinction clear in the abstract and Section 4 introduction.
- Leaving this unaddressed risks a desk rejection or a mandatory major revision on the grounds of unsubstantiated claims.

---

### C2. No statistical significance testing
- With N=50 queries and binary correctness scoring, a 24-point gap between B1 and B3 is likely significant but should be confirmed. More importantly, the B2→B3 *correctness drop* (82%→76%) needs testing — reviewers may argue the drop is noise, not an architectural effect.
- [ ] Apply McNemar's test to all pairwise correctness comparisons (B1 vs B2, B2 vs B3, B1 vs B3).
- [ ] Add 95% confidence intervals to all reported percentages.
- This is expected at Q2 level with IF 4.3 and is straightforward to add.

---

### C3. AI tool disclosure is incomplete
- Line 1293: *"the authors used ChatGPT solely as a language assistance tool"* — no version is specified.
- Taylor & Francis policy requires the **exact tool name, version, and the specific purpose** for which it was used.
- [ ] Correct to e.g. *"ChatGPT (GPT-4o, OpenAI, accessed March 2025) was used for language editing and improving readability of the manuscript."*

---

### C4. B3 (RCP) underperforms B2 on three of four metrics — this must be confronted more directly
Current results:

| Metric | B1: Naive RAG | B2: SQL Retrieval | B3: RCP | RCP vs B2 |
|--------|--------------|------------------|---------|-----------|
| Answer Correctness | 52% | 82% | 76% | ❌ −6 pts |
| Citation Accuracy | 100% | 96% | 78% | ❌ −18 pts |
| Unit Fidelity | 76% | 92% | 78% | ❌ −14 pts |
| Hallucination Rate ↓ | 48% | 18% | 2% | ✅ −16 pts |

- The paper's verify-then-summarize argument explains the correctness drop well. It does **not** explain the 18-point citation accuracy drop or the 14-point unit fidelity drop.
- [ ] Add a dedicated paragraph explaining *why* citation accuracy and unit fidelity are lower under RCP than under B2. The current "Citation accuracy gap" paragraph (Section 5.4) partially addresses citations but ignores unit fidelity.
- [ ] Consider whether the RCP's unit fidelity drop reflects a real limitation or a measurement artefact (e.g., RCP returning "no answer" for ambiguous unit queries that B2 guesses correctly).
- This is the paper's most significant intellectual tension and reviewers will probe it.

---

## II. Significant — Will Likely Trigger Major Revision if Unaddressed

### S1. LLM version is not pinned for reproducibility
- `Llama3.2:latest` (line 1153) is version-ambiguous — "latest" changes over time.
- [ ] Pin the exact model version: `llama3.2:3b` or `llama3.2:8b` as applicable.
- [ ] Note that results are obtained with a compact local model and discuss implications: would a stronger API-based model (GPT-4o, Claude 3.5) widen or narrow the B2→B3 gap?
- Reviewers will ask whether the architecture's advantages are robust to the model choice, or whether they are a compensating mechanism for a weak base model.

---

### S2. "Domain-agnostic" claim is overstated given the evaluation scope
- Both case studies are Swedish manufacturing/engineering documentation. The domains share modality (tables + text), language overlap (Swedish/English), and industry class (product catalogues / technical manuals).
- The method section correctly refers to *domain-specific* strategy libraries that must be hand-crafted per domain.
- [ ] Either: (a) soften "domain-agnostic" to "domain-adaptable" in the title and contributions, and add a sentence clarifying the generalization scope; or (b) validate on a structurally different domain (legal contracts, medical device documentation) in even a lightweight pilot.
- Option (a) requires minimal effort and eliminates a likely reviewer comment.

---

### S3. Computational complexity analysis is still commented out (Section 3.4)
- Lines 503–535 contain the full time/space/latency complexity analysis in comments — none of it appears in the compiled paper.
- [ ] Restore and integrate the complexity section. It covers $O(S \cdot P)$ strategy selection, $O(\log N)$–$O(N)$ retrieval, and session storage bounds. This analysis is expected in an architecture paper at this venue.
- A condensed version (one paragraph, not an itemized list) would serve without adding significant length.

---

### S4. Related Work does not engage with SQL-backed or workflow orchestration systems
- The new B2 baseline (SQL-backed Retrieval) performs *better than the proposed RCP* on three metrics. Yet the related work section does not discuss systems that combine structured relational storage with LLM reasoning — e.g., LangChain + SQLAlchemy, LlamaIndex with SQL retrievers, or OPERA-AR.
- [ ] Add a paragraph comparing the RCP to these systems. The key differentiator (multi-level validation gating + deterministic replay) should be articulated explicitly against named alternatives, not just against "standard LangGraph deployments."

---

### S5. No ablation isolating the contribution of individual validation stages
- The B1→B2→B3 ablation isolates structured extraction and multi-step planning. It does not isolate the contribution of the validation gates themselves.
- A reviewer could argue: "What if you run B3 without Stage 4 (function validation)? Does removing validation hurt more than removing planning?"
- [ ] Consider a lightweight Stage 4 ablation: run B3 with validation gates disabled and report the hallucination rate. Even a single number would substantially strengthen the architectural claims.

---

## III. Moderate — Should Address for a Strong Submission

### M1. B3 citation accuracy (78%) is lower than B1 (100%) and B2 (96%) — the explanation is buried
- The "Citation accuracy gap" paragraph is placed in Section 5.4 (Error Analysis) but the gap is prominent in Table 5.1. Readers will see the table before the explanation.
- [ ] Add a brief parenthetical note directly in the Table 5.1 caption or in the paragraph immediately following the table, flagging that the citation gap is explained in Section 5.4.

---

### M2. Difficulty tier analysis is defined but never used
- Easy/Medium/Hard tiers are described in Section 5.4 (lines 1232–1233) and presumably used to annotate the query sets in the appendix.
- The performance table does not stratify by tier, so the tier definitions add length without adding insight.
- [ ] Either: (a) add a tier-stratified breakdown (e.g., a 3×3 table showing correctness per tier per baseline), or (b) remove the tier definitions if they will not be used analytically.
- Option (a) is strongly preferred — it would reveal whether RCP's gains concentrate in Hard queries.

---

### M3. Flask application (Layer 3, Case I) is described but never evaluated
- Section 4.1.3 describes the application-layer web interface. It appears in no figure, no evaluation metric, and no user study.
- [ ] Either add a brief usability note or screenshot (if space permits), or trim the Layer 3 description to one sentence: "An interactive Flask interface exposes the system for exploratory querying; implementation details are available in the repository."

---

### M4. Case II has no Layer 3 description
- Case I has three layers (extraction, agentic reasoning, application interaction). Case II has two.
- [ ] Add one sentence explaining whether a Case II application layer was implemented, and if not, why.

---

### M5. Temporary database lifecycle underspecified
- Section 3.1 states the temporary database is "strictly short-lived" but does not state when it is destroyed, whether its contents are transferred to the RCP before destruction, and how deterministic replay works if it no longer exists.
- [ ] Add one to two sentences clarifying the lifecycle and the relationship between temporary artifacts and the persistent RCP ledger.

---

### M6. Error taxonomy is inconsistently applied
- Section 5.4 defines three error classes: Hallucination, Partial Answer, Field-Name Mismatch.
- Appendix tables introduce a fourth class (Parser Error) that does not appear in the Section 5.4 taxonomy.
- [ ] Either add Parser Error to the taxonomy, or explain in the appendix caption why it is excluded from the main taxonomy.

---

## IV. Minor — Presentation and Compliance

### P1. Case II introduction contains two drafty, run-on sentences (line 909)
- "this case targets yet again, a heterogeneous and multilingual content..." — lowercase "this", comma splice, redundant "yet again."
- "The case hence motivate explicit orchestration..." — subject-verb agreement error.
- [ ] Proofread lines 909–913 carefully. These are the first sentences of a major subsection.

---

### P2. `func_analyse_data` footnote is still an awkward workaround
- The footnote at line 708 bridges "Analyse With LLM" (table label) and `func_analyse_data` (callable ID).
- [ ] Use the callable identifier consistently in all tables, explain the convention once in Section 3.3 (Function Library), and eliminate the footnote.

---

### P3. Commented-out sections add confusion during review
- Multiple large commented-out blocks remain in the source (old Section 2, old evaluation setup, old limitations subsection). These are invisible in the compiled PDF but create noise if editors review source files.
- [ ] Clean up commented code before final submission.

---

### P4. Data Availability Statement excludes Case II repository
- Line 1311 references only the Hydroscand repository. `oscik559/Project_Saab` is mentioned in-text (line 1160) but not in the formal Data Availability Statement.
- [ ] Either add the Saab repository to the Data Availability Statement, or note its confidential status there.

---

### P5. Verify GitHub repositories are public and contain described code
- [ ] Confirm both `oscik559/Hydroscand_Produktbok` and `oscik559/Project_Saab` are publicly accessible with representative code, as reviewers may inspect them.

---

## Summary Scorecard

| Dimension | v1 Assessment | v2 Assessment |
|---|---|---|
| Evaluation completeness | ❌ Critical — tables unfinished | ✅ Now complete |
| Baseline quality | ❌ Strawman at 10% | ✅ Strong three-tier ablation |
| Results vs claims alignment | ❌ Abstract contradicted data | ✅ Now coherent |
| Statistical rigor | ❌ Absent | ❌ Still absent — needs McNemar's test |
| Case II quantitative results | ❌ Missing | ❌ Still missing |
| "Domain-agnostic" claim | ⚠️ Overstated | ⚠️ Still overstated |
| LLM reproducibility | ⚠️ Unpinned | ⚠️ Still unpinned |
| Discussion of RCP vs B2 gap | — | ⚠️ Partially addressed, needs expansion |
| Writing quality | ⚠️ Some drafty sections | ⚠️ Minor issues remain |
| T&F compliance | ❌ Wrong AI tool name | ⚠️ Tool listed, version missing |

---

## Revised Pre-Submission Checklist

- [ ] **C1** — Add Case II quantitative results, or explicitly reframe it as qualitative demonstration
- [ ] **C2** — Add McNemar's test and 95% confidence intervals for all pairwise comparisons
- [ ] **C3** — Fix AI disclosure: add tool version and specific purpose
- [ ] **C4** — Explain the citation accuracy and unit fidelity drops under RCP vs B2
- [ ] **S1** — Pin exact LLM version; add sensitivity note
- [ ] **S2** — Soften "domain-agnostic" to "domain-adaptable" or add third-domain pilot
- [ ] **S3** — Restore computational complexity analysis from comments
- [ ] **S4** — Add Related Work paragraph comparing to SQL-backed LLM systems
- [ ] **S5** — Add validation-gate ablation (Stage 4 disabled) or similar
- [ ] **M1** — Flag citation accuracy gap near Table 5.1, not only in Section 5.4
- [ ] **M2** — Add tier-stratified results or remove tier definitions if unused
- [ ] **M3** — Trim Layer 3 description (Case I) or add evaluative content
- [ ] **M4** — Add one sentence on Case II Layer 3 status
- [ ] **M5** — Clarify temporary database lifecycle
- [ ] **M6** — Make error taxonomy consistent (add or exclude Parser Error)
- [ ] **P1** — Proofread Case II introduction (lines 909–913)
- [ ] **P2** — Standardize function naming; remove func_analyse_data footnote
- [ ] **P3** — Remove commented-out source blocks before final submission
- [ ] **P4** — Update Data Availability Statement to address Case II repository

---
---

# Length and Redundancy Audit

The manuscript is substantially longer than a typical AAI journal article (target: ~8,000–10,000 words for the main body; the current draft appears to exceed this). The following sections identify specific areas of repetition, padding, and unnecessary detail, with concrete cut or merge recommendations.

---

## 1. Introduction — Over-motivated (save ~200 words)

The introduction contains two nearly independent motivation passes. Paragraphs 1–2 motivate from the LLM/RAG failure angle. Paragraph 3 re-motivates from the agentic framework angle. Both reach the same conclusion: existing systems lack structured validation and traceability.

**Cut recommendation:** Merge paragraphs 1–3 into two tighter paragraphs. The Freire et al. citation and the RAPTOR system discussion (paragraph 2) can be condensed to one sentence each. The current paragraph ending "these challenges motivate extraction pipelines that preserve provenance anchors..." is a complete and sufficient transition; the detailed elaboration before it can be halved.

---

## 2. Related Work → Method transition paragraph (delete entirely, save ~80 words)

Lines 262–263 contain an explicit transition paragraph that summarizes the limitations "identified in existing approaches" before introducing the Method section. This paragraph:
- Repeats points already made in the Related Work subsections
- Previews content already stated in the Introduction contributions list
- Adds nothing not captured by the section header itself

**Cut recommendation:** Delete the paragraph. Let the section break speak for itself.

---

## 3. Method section opening paragraph repeats the Introduction (save ~100 words)

Lines 272–273 (Section 3 opening) state: *"Engineering document reasoning requires coordinated execution of specialized agents, structured validation at multiple levels, and complete auditability of reasoning chains. This section presents a domain-agnostic agentic framework..."*

This is a near-verbatim restatement of the Introduction's framing. Every section in the paper opens with a similar motivating sentence restating why engineering documents are hard.

**Cut recommendation:** Replace the Method section's opening paragraph with a single orienting sentence: *"The proposed framework addresses these requirements through a six-stage control loop backed by a relational persistence layer; the following subsections detail each component."* Then proceed directly to Section 3.1.

---

## 4. Case I domain introduction is thesis-length, not journal-length (save ~150 words)

Section 4.1 (Hydroscand case) opens with three paragraphs:
1. Paragraph 1 — General motivation for hydraulic product catalogues
2. Paragraph 2 — Specific extraction challenges (merged cells, thread notation, Swedish terminology)
3. Paragraph 3 — "This environment thus presents an appropriate proof-of-concept domain..."

Paragraph 3 is entirely justificatory and reads like thesis writing. A journal reader accepts that the authors chose their case study deliberately — they do not need a paragraph explaining why.

**Cut recommendation:** Delete paragraph 3 entirely. Fold the one useful sentence ("Successfully demonstrating reliable extraction and reasoning here directly tests the framework's ability...") into the end of paragraph 2 if needed.

---

## 5. Case II introduction repeats Case I's framing (save ~120 words)

Section 4.2 opens with two paragraphs (lines 909–913) explaining that:
- This case involves cross-document consistency and revision fidelity
- This case has heterogeneous, multilingual content
- These features motivate explicit orchestration

All three points were already made in the Introduction and Related Work when motivating the framework. Case II's opening paragraph should simply orient the reader to what is new and different about this case, not re-motivate the framework.

**Cut recommendation:** Compress lines 909–913 to: *"The second case studies revision-controlled aerospace documentation in collaboration with Saab AB. Unlike Case I, where queries target a well-defined product catalogue, Case II requires cross-document reasoning with applicability constraints, revision scope resolution, and multimodal evidence fusion across 54 documents and 451 tables."* (One paragraph, ~50 words, replaces ~120.)

---

## 6. The two worked examples are disproportionately detailed (save ~250–300 words)

Each case study contains a full worked example with:
- A dedicated subsection heading
- A prose narrative of the query and requirements
- A per-function enumerated list (4 items for Case I, 6 for Case II) each with a descriptive paragraph
- Four or more sub-captioned tables showing goal, strategy, and function instances

The Case I worked example alone occupies approximately 600–700 words of prose plus four tables. For a journal audience that can inspect the appendix, this level of trace narration in the main body is excessive.

**Cut recommendation:**
- In Case I: Remove the per-function enumerated list (items i–iv, lines 796–812). The four subtables (Tables 4a–4d) already show the same information visually. Replace with: *"Execution proceeds through four function calls (Tables 4a–4d): product code extraction, database lookup, attribute extraction, and LLM synthesis. Each step is validated before progression; failure at any stage routes control back to StrategyValidate."*
- In Case II: The worked example is already leaner. Keep it, but trim the goal definition and strategy selection narrative paragraphs (lines 1062–1066) to one sentence each, as the corresponding tables convey the same content.
- Combined saving: approximately 250–300 words.

---

## 7. Section 3.5 (In-Session Instantiation) is over-long and partially redundant (save ~150 words)

The paragraph beginning "The in-session tables thus serve as a normalized execution ledger..." (line 463) runs for approximately 200 words and covers:
- What the in-session tables store (already described in Section 3.2)
- Why this enables deterministic replay (already stated in the RCP subsection)
- Why policy can be adapted by updating library entries rather than rewriting code (stated again)

The same section then ends with a summary sentence that recaps all three points again ("In effect, the RCP operationalizes a data-driven 'goal → strategy → agent → validation' loop...").

**Cut recommendation:** Cut this paragraph by half. Keep the first sentence (execution ledger framing) and the last sentence (data-driven loop summary). Remove the middle — it repeats points already made in Section 3.2.

---

## 8. Strategy selection "note" paragraph adds a caveat that should be in Limitations (save ~60 words)

Lines 495–495: *"Note that the current LLM-guided selection approach, while traceable, introduces a degree of non-determinism at the selection step. A planned code-level enhancement will replace this..."*

This is a limitation/future work statement placed mid-subsection, where it breaks the architectural description. It also duplicates content that should appear in Section 6 (Discussion and Limitations).

**Cut recommendation:** Move this note to Section 6 under Limitations. Remove from Section 3.4.

---

## 9. Discussion repeats Error Analysis language almost verbatim (save ~80 words)

Compare:

- **Section 5.4 (Error Analysis), line 1257:** *"This shifts system behaviour from generate–then–justify toward verify–then–summarize. Rather than emitting unsupported values, the system fails explicitly when sufficiency conditions are unmet."*
- **Section 6 (Discussion), line 1257:** Near-identical phrasing appears again: *"gates progression by requiring schema validity, provenance completeness, and plausibility checks before synthesis. This shifts system behaviour from generate–then–justify toward verify–then–summarize."*

**Cut recommendation:** In the Discussion, replace the repeated verify-then-summarize language with a forward reference: *"As discussed in the error analysis (Section 5.4), this verify-then-summarize design is appropriate for engineering contexts where..."* and proceed directly to the scalability/governance argument.

---

## 10. Function library descriptions in the text duplicate the tables (save ~100 words)

Section 4.1.2 describes the function library in a paragraph (line 645) and then presents a seven-row table. The paragraph restates what is in the table (atomic capabilities, standard interface, declared inputs/outputs). Similarly in Case II, lines 993–994 describe the function library before presenting Table 4.

**Cut recommendation:** For each case, replace the function library prose paragraph with a single sentence that simply directs the reader to the table: *"The strategy templates in Table 3 are executed through the functions listed in Table 4, each adhering to a standardized interface (success: bool, result: dict)."* Cut the rest.

---

## Summary of Length Savings

| Section | Type | Estimated saving |
|---------|------|-----------------|
| Introduction | Merge motivation passes | ~200 words |
| Related Work → Method transition | Delete redundant paragraph | ~80 words |
| Method opening | Trim to one sentence | ~100 words |
| Case I domain justification paragraph | Delete | ~150 words |
| Case II opening | Compress to one paragraph | ~120 words |
| Worked Example Case I (enumerated list) | Remove, keep tables | ~250 words |
| Section 3.5 In-Session Instantiation | Cut middle half | ~150 words |
| Strategy selection limitation note | Move to Limitations | ~60 words |
| Discussion (verify-then-summarize repeat) | Forward-reference instead | ~80 words |
| Function library prose (both cases) | Replace with one-liners | ~100 words |
| **Total estimated saving** | | **~1,290 words** |

Removing approximately 1,200–1,300 words from the main body would bring the paper within a more appropriate word count for this venue, eliminate reviewer fatigue from repetition, and allow the genuinely novel content — the evaluation, the ablation design, and the error analysis — to carry more weight.
