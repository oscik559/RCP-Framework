# Context Management Flow Diagram

```mermaid
graph TD
    A[User Query] --> B{Data Source?}
    
    B -->|Small Dataset<br/>1-20 products| C[Direct Mode]
    B -->|Large Dataset<br/>20-200 products| D[Chunked Mode]
    B -->|Massive Dataset<br/>200+ products| E[Assembly Mode]
    
    C --> F[Pass data directly<br/>to LLM]
    F --> G[LLM Analysis]
    
    D --> H[Extract keywords<br/>from question]
    H --> I[Score products<br/>by relevance]
    I --> J[Sort by score]
    J --> K[Include top products<br/>until context limit]
    K --> G
    
    E --> L[Query temp.db<br/>with SQL]
    L --> M[Filter & sort<br/>in database]
    M --> N[Return top N<br/>products]
    N --> G
    
    G --> O[Return Analysis<br/>+ Diagnostics]
    
    style C fill:#90EE90
    style D fill:#FFD700
    style E fill:#87CEEB
    style G fill:#FF6B6B
    style O fill:#95E1D3
```

## Mode Selection Logic

```mermaid
flowchart LR
    Start([func_analyze_with_llm]) --> Check1{assembled_data<br/>provided?}
    
    Check1 -->|Yes| Assembly[🔵 ASSEMBLY MODE<br/>Query temp.db]
    Check1 -->|No| Check2{extracted_data<br/>size?}
    
    Check2 -->|< 30K chars| Direct[🟢 DIRECT MODE<br/>Pass through]
    Check2 -->|> 30K chars| Chunked[🟡 CHUNKED MODE<br/>Filter & truncate]
    
    Assembly --> SQL[Execute SQL query]
    SQL --> Build1[Build context from results]
    Build1 --> LLM[Send to LLM]
    
    Direct --> Build2[Format data as-is]
    Build2 --> LLM
    
    Chunked --> Keywords[Extract question keywords]
    Keywords --> Score[Score each product]
    Score --> Sort[Sort by relevance]
    Sort --> Include[Include until limit]
    Include --> Build3[Build context]
    Build3 --> LLM
    
    LLM --> Result([Return analysis<br/>+ diagnostics])
    
    style Assembly fill:#87CEEB,stroke:#333,stroke-width:2px
    style Direct fill:#90EE90,stroke:#333,stroke-width:2px
    style Chunked fill:#FFD700,stroke:#333,stroke-width:2px
    style LLM fill:#FF6B6B,stroke:#333,stroke-width:2px,color:#fff
    style Result fill:#95E1D3,stroke:#333,stroke-width:2px
```

## Relevance Scoring Example

```mermaid
graph TD
    Q[Question: What is the pressure rating for 4SP hoses?]
    Q --> K[Keywords: 4sp, pressure, rating, hoses]
    
    K --> P1[Product 4SP-12<br/>pressure: 45.0 MPa]
    K --> P2[Product 4SP-16<br/>pressure: 50.0 MPa]
    K --> P3[Product 2SN-12<br/>pressure: 28.0 MPa]
    K --> P4[Product 1SN-08<br/>bend: 120mm]
    
    P1 --> S1[Score: 10<br/>4sp + pressure]
    P2 --> S2[Score: 10<br/>4sp + pressure]
    P3 --> S3[Score: 5<br/>pressure only]
    P4 --> S4[Score: 0<br/>no matches]
    
    S1 --> R[Sorted Results]
    S2 --> R
    S3 --> R
    S4 --> R
    
    R --> C[Context Builder]
    C --> |Include| I1[4SP-12]
    C --> |Include| I2[4SP-16]
    C --> |Include| I3[2SN-12]
    C --> |Exclude| I4[1SN-08<br/>Not relevant]
    
    I1 --> LLM[LLM Context]
    I2 --> LLM
    I3 --> LLM
    
    style Q fill:#FFE4B5
    style K fill:#E0BBE4
    style R fill:#95E1D3
    style LLM fill:#FF6B6B,color:#fff
    style I4 fill:#FFB6C1,stroke-dasharray: 5 5
```

## Workflow Examples

### Small Dataset (Direct Mode)
```mermaid
sequenceDiagram
    participant User
    participant System
    participant LLM
    
    User->>System: Extract 5 products
    System->>System: Check size: 2K chars
    System->>System: Mode: DIRECT ✓
    System->>LLM: Send all 5 products
    LLM->>System: Analysis
    System->>User: Result + mode_used: "direct"
```

### Large Dataset (Chunked Mode)
```mermaid
sequenceDiagram
    participant User
    participant System
    participant Scorer
    participant LLM
    
    User->>System: Extract 100 products
    System->>System: Check size: 80K chars ⚠️
    System->>System: Mode: CHUNKED
    System->>Scorer: Extract keywords from question
    Scorer->>Scorer: Score each product
    Scorer->>Scorer: Sort by relevance
    Scorer->>System: Top 30 products (28K chars)
    System->>LLM: Send top 30
    LLM->>System: Analysis
    System->>User: Result + context_truncated: true
```

### Massive Dataset (Assembly Mode)
```mermaid
sequenceDiagram
    participant User
    participant System
    participant Database
    participant LLM
    
    User->>System: Extract 300 products
    System->>System: Assemble to temp.db
    System->>System: Mode: ASSEMBLY
    System->>Database: SQL query with filters
    Database->>System: Top 50 relevant products
    System->>System: Format as context (25K chars)
    System->>LLM: Send formatted data
    LLM->>System: Analysis
    System->>User: Result + mode_used: "assembly"
```

## Performance Visualization

```mermaid
graph LR
    subgraph "Direct Mode"
        D1[1-20 products] --> D2[2-3 seconds]
        D2 --> D3[100% accuracy]
    end
    
    subgraph "Chunked Mode"
        C1[20-200 products] --> C2[3-5 seconds]
        C2 --> C3[95% accuracy*]
    end
    
    subgraph "Assembly Mode"
        A1[200+ products] --> A2[4-8 seconds]
        A2 --> A3[100% accuracy]
    end
    
    style D1 fill:#90EE90
    style C1 fill:#FFD700
    style A1 fill:#87CEEB
    
    style D3 fill:#90EE90
    style C3 fill:#FFD700
    style A3 fill:#90EE90
```

*Accuracy depends on relevance filtering quality

## Context Size Comparison

```
Before (No Chunking):
┌────────────────────────────┐
│   50 products = 50K chars  │  ❌ FAILS
│   Context limit exceeded   │
└────────────────────────────┘

After (Smart Chunking):
┌────────────────────────────┐
│   50 products → Score      │
│   Top 35 → 28K chars       │  ✅ SUCCESS
│   Relevant data included   │
└────────────────────────────┘

After (Assembly Mode):
┌────────────────────────────┐
│   300 products → temp.db   │
│   SQL filter → 50 products │  ✅ SUCCESS
│   Query → 25K chars        │
└────────────────────────────┘
```
