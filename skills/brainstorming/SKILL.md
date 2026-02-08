---
name: brainstorming
description: >
  Facilitate structured brainstorming sessions for design, architecture, and problem-solving. Generates multiple approaches, evaluates trade-offs, and helps teams explore creative solutions systematically.
metadata:
  author: corporate-ai-cli
  version: "1.0"
  category: planning
---

# Brainstorming

Facilitate structured brainstorming sessions to explore multiple solutions, evaluate trade-offs, and make informed design decisions.

## Overview

Effective brainstorming generates diverse ideas, evaluates them objectively, and helps teams converge on the best solution. This skill provides a framework for productive ideation sessions.

## Brainstorming Methodology

### Phase 1: Define the Problem

**Goal**: Clearly articulate what you're trying to solve.

**Steps**:

1. **State the Problem**:
   - What is the current situation?
   - What is the desired outcome?
   - Why is this important?

2. **Define Constraints**:
   - Time constraints
   - Budget constraints
   - Technical constraints
   - Resource constraints
   - Policy/compliance requirements

3. **Identify Success Criteria**:
   - What does a good solution look like?
   - How will you measure success?
   - What are must-haves vs nice-to-haves?

**Template**:
```markdown
## Problem Statement

**Current Situation**:
[Describe the current state and the problem]

**Desired Outcome**:
[What we want to achieve]

**Why This Matters**:
[Impact and importance]

**Constraints**:
- [Constraint 1]
- [Constraint 2]
- [Constraint 3]

**Success Criteria**:
1. [Criterion 1]
2. [Criterion 2]
3. [Criterion 3]

**Must Have**:
- [Non-negotiable requirement]

**Nice to Have**:
- [Optional feature or benefit]
```

### Phase 2: Generate Ideas

**Goal**: Create a diverse set of potential solutions without judgment.

**Rules for Idea Generation**:
- No criticism during generation phase
- Encourage wild ideas
- Build on others' ideas
- Aim for quantity over quality initially
- Consider diverse perspectives

**Techniques**:

#### 1. Free Association
Start with the problem and branch out:
```
Problem: Slow database queries
  ↓
Caching → Redis → Memcached → In-memory cache
Indexing → B-tree → Hash index → Composite index
Denormalization → Read replicas → Materialized views
Query optimization → Query rewriting → ORM optimization
```

#### 2. SCAMPER Method
- **S**ubstitute: What can be substituted?
- **C**ombine: What can be combined?
- **A**dapt: What can be adapted from elsewhere?
- **M**odify: What can be modified or magnified?
- **P**ut to another use: How else can this be used?
- **E**liminate: What can be eliminated?
- **R**everse: What can be reversed or rearranged?

#### 3. Analogies
- How do other industries solve similar problems?
- What natural systems deal with similar challenges?
- What successful products have similar characteristics?

#### 4. Perspective Shifting
- How would [expert] solve this?
- What would a startup do? A large enterprise?
- How would we solve this with 10x the budget? 1/10 the budget?
- How would we solve this if we had to launch tomorrow?

**Template**:
```markdown
## Ideas Generated

### Idea 1: [Name]
**Description**: [Brief description]
**Inspiration**: [Where the idea came from]

### Idea 2: [Name]
**Description**: [Brief description]
**Inspiration**: [Where the idea came from]

[Continue for all ideas...]

**Total Ideas Generated**: [X]
```

### Phase 3: Organize and Categorize

**Goal**: Group similar ideas and identify patterns.

**Categorization Approaches**:

#### By Approach Type
- **Incremental**: Small improvements to existing system
- **Transformational**: Complete redesign
- **Hybrid**: Mix of old and new

#### By Complexity
- **Simple**: Quick to implement, low risk
- **Moderate**: Requires some work, medium risk
- **Complex**: Significant effort, higher risk

#### By Technology
- **Frontend solutions**
- **Backend solutions**
- **Database solutions**
- **Infrastructure solutions**

**Template**:
```markdown
## Organized Ideas

### Category: Caching Solutions
1. Redis cache
2. In-memory cache
3. CDN caching

### Category: Query Optimization
1. Add database indexes
2. Query rewriting
3. ORM optimization

### Category: Architecture Changes
1. Read replicas
2. Denormalization
3. Event-driven architecture
```

### Phase 4: Evaluate Solutions

**Goal**: Objectively assess each idea against criteria.

**Evaluation Framework**:

#### 1. Impact vs Effort Matrix

```
High Impact, Low Effort          High Impact, High Effort
    (Quick Wins)                     (Major Projects)
        │                                 │
        │                                 │
────────┼─────────────────────────────────┼────────
        │                                 │
        │                                 │
Low Impact, Low Effort           Low Impact, High Effort
    (Fill-ins)                       (Time Wasters)
```

#### 2. Scoring Matrix

| Solution | Impact | Feasibility | Cost | Risk | Total |
|----------|--------|-------------|------|------|-------|
| Solution A | 9 | 7 | 8 | 6 | 30 |
| Solution B | 7 | 9 | 9 | 8 | 33 |
| Solution C | 10 | 4 | 5 | 3 | 22 |

Scoring: 1-10 (10 = best)

#### 3. Pros and Cons

```markdown
### Solution: Redis Caching

**Pros**:
- Fast performance (microsecond latency)
- Mature, battle-tested technology
- Rich data structures
- Easy to scale horizontally

**Cons**:
- Additional infrastructure to maintain
- Adds complexity to deployment
- Cache invalidation challenges
- Costs money for managed service

**Risk Assessment**:
- Technical risk: Low
- Schedule risk: Low
- Maintenance risk: Medium
```

#### 4. Trade-offs Analysis

```markdown
### Solution Comparison

**Option 1: Redis Cache**
- ✓ Fastest performance
- ✓ Proven technology
- ✗ Additional infrastructure
- ✗ Cache invalidation complexity

**Option 2: Database Optimization**
- ✓ No new infrastructure
- ✓ Simpler architecture
- ✗ Limited performance gains
- ✗ May require schema changes

**Option 3: Materialized Views**
- ✓ Good performance
- ✓ Stays within database
- ✗ Refresh overhead
- ✗ Staleness concerns
```

### Phase 5: Converge on Solution

**Goal**: Select the best solution or combination of solutions.

**Decision-Making Approaches**:

#### 1. Weighted Decision Matrix

```markdown
## Decision Matrix

| Criteria | Weight | Solution A | Solution B | Solution C |
|----------|--------|------------|------------|------------|
| Performance | 30% | 9 (2.7) | 7 (2.1) | 8 (2.4) |
| Cost | 20% | 6 (1.2) | 9 (1.8) | 7 (1.4) |
| Complexity | 25% | 7 (1.75) | 9 (2.25) | 6 (1.5) |
| Maintainability | 25% | 8 (2.0) | 8 (2.0) | 7 (1.75) |
| **Total** | | **7.65** | **8.15** | **7.05** |

**Winner**: Solution B
```

#### 2. Elimination Method

Progressively eliminate solutions that don't meet must-have criteria:

```markdown
## Elimination Process

**Round 1: Must meet performance requirements (>100 RPS)**
- ✓ Solution A: 150 RPS
- ✓ Solution B: 200 RPS
- ✗ Solution C: 80 RPS - ELIMINATED

**Round 2: Must be implementable in 2 weeks**
- ✓ Solution A: 10 days
- ✗ Solution B: 20 days - ELIMINATED

**Winner**: Solution A
```

#### 3. Hybrid Approach

Combine the best elements from multiple solutions:

```markdown
## Hybrid Solution

**Chosen Elements**:
- Use Redis for caching (from Solution A)
- Implement query optimization (from Solution B)
- Add database indexes (from Solution B)

**Rationale**:
This combination provides the best balance of performance improvement
and implementation simplicity. Redis handles the hot data path while
query optimization improves the cold path.

**Implementation Order**:
1. Add database indexes (quick win)
2. Optimize slow queries (medium effort)
3. Implement Redis cache (larger effort)
```

## Output Format

```markdown
# Brainstorming Session: [Topic]

**Date**: [Date]
**Participants**: [Names or "AI + User"]
**Duration**: [Time spent]

---

## Problem Statement

[From Phase 1]

---

## Ideas Generated

[From Phase 2]

**Total Ideas**: [X]

---

## Organized Ideas

[From Phase 3]

---

## Evaluation

[From Phase 4]

### Top 3 Solutions

1. **[Solution Name]** (Score: X/Y)
   - [Key benefit]
   - [Key drawback]

2. **[Solution Name]** (Score: X/Y)
   - [Key benefit]
   - [Key drawback]

3. **[Solution Name]** (Score: X/Y)
   - [Key benefit]
   - [Key drawback]

---

## Recommended Solution

[From Phase 5]

**Chosen Approach**: [Name]

**Rationale**: [Why this solution]

**Trade-offs Accepted**: [What we're giving up]

**Implementation Strategy**:
1. [Phase 1]
2. [Phase 2]
3. [Phase 3]

**Success Metrics**:
- [Metric 1]: [Target]
- [Metric 2]: [Target]

---

## Next Steps

1. [Action item 1]
2. [Action item 2]
3. [Action item 3]

**Owner**: [Who will drive this]
**Timeline**: [When this will happen]

---

## Parking Lot

**Ideas to Revisit Later**:
- [Interesting idea not chosen now]
- [Alternative approach for future]

**Questions to Answer**:
- [Unresolved question]
- [Need more information about]
```

## Brainstorming for Different Scenarios

### Architecture Design
Focus on: Scalability, maintainability, extensibility
Key questions:
- How will this scale?
- What are the failure modes?
- How easy is it to change later?

### Feature Design
Focus on: User experience, value, feasibility
Key questions:
- What problem does this solve for users?
- What's the MVP?
- How will we measure success?

### Bug Investigation
Focus on: Root cause, prevention, fix approach
Key questions:
- Why did this happen?
- How can we prevent it in the future?
- What's the least risky fix?

### Performance Optimization
Focus on: Bottlenecks, quick wins, long-term improvements
Key questions:
- Where is the bottleneck?
- What gives us the most improvement for least effort?
- What are the diminishing returns?

## Tips for Effective Brainstorming

### Do:
- Start with a clear problem statement
- Generate many ideas before evaluating
- Consider diverse perspectives
- Use structured evaluation criteria
- Document everything
- Be open to unconventional ideas
- Build on others' suggestions

### Don't:
- Criticize ideas during generation phase
- Jump to the first solution
- Let one voice dominate
- Ignore constraints
- Rush the process
- Forget to document
- Make decisions without evaluation

## Tools and Techniques

### Visual Techniques
- Mind maps
- Affinity diagrams
- Flowcharts
- Decision trees

### Structured Thinking
- Five Whys (root cause)
- First Principles thinking
- Inversion (what would make this fail?)
- Pre-mortem (assume it failed, why?)

### Collaborative Techniques
- Round robin (everyone contributes)
- Silent brainstorming (write then share)
- Build on each other
- Role playing different stakeholders
