# Recommendations for Section 4: Hydroscand Case Study

## 1. Status Assessment
The current draft of Section 4 is **strong and technically accurate**. It correctly reflects the architectural split between:
- **Layer 1 (Extraction):** VLM-based PDF parsing.
- **Layer 2 (Reasoning):** The 6-stage control loop and RCP.
- **Layer 3 (Application):** The interface.

The alignment between the paper's claims (traceability, modularity) and the codebase (`agentic_schema.sql`, `state_graph.py`) is excellent.

## 2. Recommendations for Improvement

### A. Terminology Synchronization
The strategy names in the paper (Table 4.4) differ slightly from the codebase (`templates.py`).
- **Paper:** `product_search`, `spec_lookup`, `compatibility_check`
- **Code:** `CONTEXTUAL PRODUCT SEARCH`, `DIRECT SPECIFICATION LOOKUP`, `STANDARD & COMPLIANCE LOOKUP`

**Action:** Update Table 4.4 in the paper to either use the exact Code usage or explicitly state that the paper uses simplified keys. Using the exact names (e.g., "Contextual Product Search") adds authenticity.

### B. Highlight "Design-Time" Configuration
The claim of "declarative behavior" is a key winning point.
**Action:** Include a brief code snippet or explanation of `templates.py`. Show how strategies are defined as straightforward Python tuples/lists that get pushed to the SQL database. This proves that changing behavior doesn't require rewriting the *engine* (`state_graph.py`), only the *data*.

### C. Concrete Validation Examples
You mention validation gates. To make this compelling:
**Action:** Provide one concrete example of a validation failure and recovery.
- *Example:* "Agent extracted '1/2' without a thread type. `FunctionValidate` rejected it. The strategy retried with a `spec_lookup` targeting the 'connection type' column, successfully resolving it to 'G 1/2'."

### D. Quantitative Metrics (Adaptation Effort)
To fully sell the "Domain-Agnostic" aspect:
**Action:** Estimate and report the "Cost of Adaptation".
- How many lines of code were unique to Hydroscand? (Likely just the agents in `function_library.py` and templates in `templates.py`).
- Contrast this with the size of the core engine (`state_graph.py`, `workflow_nodes.py`) which remained unchanged.
- *Draft Statement:* "Applying the framework to the domain required only ~400 LOC of domain-specific agents and 50 database rows for strategy templates, leaving the 2,000+ LOC orchestration engine untouched."

## 3. Proposed "Future Work" for Case 1
- **VLM-Assisted Validation:** Using the VLM not just for extraction, but as a "judge" in the `FunctionValidate` step to verify if the extracted text visually matches the cropped table image.
- **Learning Strategies:** Use the `StrategySuccess` flag in `StrategyInSession` to automatically downrank failing strategies over time.
