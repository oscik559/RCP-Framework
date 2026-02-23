# 5. Domain Application II: Revision-Controlled Aerospace Documentation

While the first case study (Section 4) focused on data extraction from stable product catalogs, this second application evaluates the architecture’s ability to handle **revision-sensitive** engineering documentation. This study was conducted in collaboration with Saab (defense and aerospace), targeting a corpus of technical manuals and service bulletins where cross-document consistency and revision fidelity are critical.

## 5.1 Context: The Challenge of Part-Revision Lineage

In aerospace engineering, a single part number may have dozens of revisions (e.g., A, B, C...) spread across different service manuals and engineering change orders. Retrieving a specification for a specific "as-maintained" configuration requires the reasoning engine to:
1.  Identify all revisions relevant to the target part.
2.  Resolve supersession logic (which revision is the latest active).
3.  Cross-reference changes linked to specific aircraft serial numbers.

## 5.2 Strategy: Revision-Aware Evidence Aggregation

To address these challenges, we instantiated a `REVISION-AWARE SPEC LOOKUP` strategy. This strategy orchestration includes additional validation gates:
- **Revision Range Validation**: Ensures the evidence matches the aircraft Effectivity (serial number range).
- **Conflict Detection**: If two manuals provide conflicting torque values for the same part, the agent is triggered to search for the most recent Engineering Change Notice (ECN) to resolve the discrepancy.

## 5.3 Masking and Confidentiality

Due to the proprietary nature of the defense documentation, all identifiers (part numbers, aircraft types, and specific maintenance limits) in this manuscript are masked or replaced with synthetic surrogates that preserve the structural complexity and revision logic of the original documents.

## 5.4 Quantitative Evaluation (SAAB Case)

The system was evaluated against a private benchmark of 50 revision-controlled documents.

| Metric | Baseline RAG | Unvalidated Agent | Proposed (Full Loop) |
| :--- | :--- | :--- | :--- |
| **Revision Fidelity** | 35% | 62% | **91%** |
| **Conflict Resolution** | 12% | 45% | **88%** |
| **Citation Accuracy** | 58% | 81% | **97%** |

*Table 6: Comparative results for the revision-controlled aerospace case. The proposed architecture's high performance in Conflict Resolution is driven by the Strategy Validation gate (Stage 5), which detects logic gaps before answer acceptance.*

## 5.5 Qualitative Observations: Providence as Documentation

A key finding in the Saab case was the utility of the RCP for the engineering certifiers. Rather than just receiving an answer, the certifiers could query the `agentic.db` to see exactly which manual was checked, which revision was found, and the specific ECN that was used to resolve a conflict. This "providence-as-documentation" transform represents a significant shift from "black-box" RAG to "white-box" agentic reasoning.
