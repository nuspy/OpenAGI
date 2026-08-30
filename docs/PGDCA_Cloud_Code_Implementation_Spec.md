# Persistent Goal-Directed Cognitive Architecture (PGDCA)
## Complete Technical Implementation Specification for Cloud Code

**Project type:** Autonomous cognitive / agentic architecture  
**Primary implementation target:** Cloud Code  
**Status:** Architecture and implementation specification  
**Version:** 1.2  
**Date:** 2026-08-30

> Revision 1.1 applies the approved modifications recorded in `ANALISI_E_PROPOSTE.md`: goal governance and corrigibility, prompt-injection defense, bounded autonomy budgets, vertical-slice phasing with a Phase 0 minimum viable loop, event sourcing and deterministic replay, calibrated scoring, causal-graph and policy-learning guardrails, cold start, tool-acquisition security, compliance and privacy, two-tier guardrails, decision supervisor, GUI/API layer, ports & adapters, deliberation, imported skills and MCP servers, and the normative canonical schema (Appendix A). Section numbering shifted with the inserted sections.

> Revision 1.2 formalizes the user requirements M29–M33 recorded in `ANALISI_E_PROPOSTE.md` (rev. 4–5), previously specified only by the reference implementation and phase documents: cross-AI review with a per-checkpoint consensus matrix (§93), the grounding check inside the guardrail system (§94), exogenous directives and facts with consensus weaving and re-evaluating CRUD (§95), extended human–AI interaction — change-set resolutions, scenario threads, AI-initiated consultations (§96), and the feature-settings surface (§97). Sections 93–97 are appended; existing numbering is unchanged. §65 gains the event types introduced since 1.1. The voice application's correct name is **CallAPICall** (earlier documents wrote "CallAPICall"; corrected on the owner's instruction — the paper carries the old name until its next tracked-changes revision).

---

# 1. Executive Summary

This document specifies an autonomous cognitive architecture whose purpose is to turn one or more persistent high-level goals into continuously evaluated, adaptive, long-horizon behavior.

The central design decision is that the system is **not an LLM wrapper and not merely a task planner**. An LLM is a reasoning component inside a larger deterministic orchestration and control system.

The system must:

- maintain persistent goals and motivations;
- decompose goals into objectives, targets, sub-targets, tasks and actions;
- continuously re-evaluate whether those subordinate goals remain useful;
- represent the world as a dynamic graph of goals, factors, resources, capabilities and causal relationships;
- represent positive, negative, required, blocking, risky, enabling and antagonistic relationships;
- assign weights, costs, probabilities, utility, risk, substitutability and other attributes to relationships;
- propagate direct and indirect effects through the graph;
- detect conflicts between different goals;
- resolve conflicts through prioritization, mitigation, substitution, scaling, temporal separation and creation of new enabling factors;
- discover, acquire and create tools/capabilities;
- maintain a persistent audit journal;
- evaluate past decisions, not only outcomes;
- abstract concrete decisions into reusable patterns and policies;
- learn when a policy works, when it fails and under what conditions;
- maintain episodic, semantic, procedural and meta-memory;
- use retrieval agents so the main reasoning context is not overloaded;
- maintain a self-model of capabilities, weaknesses, reliability and failure modes;
- use web research, software tools, browser automation, communication channels and other external tools;
- cooperate with humans and other AIs by text and voice;
- analyze reasons/motivations behind goals, decisions and observed behavior;
- continuously search for new opportunities instead of merely completing a predefined plan.

The architecture should behave less like a chatbot and more like a persistent goal-directed cognitive system.

---

# 2. Core Architectural Principle

The fundamental separation is:

**LLM = reasoning engine**  
**Controller/orchestrator = behavioral control mechanism**  
**Memory = temporal continuity**  
**World/causal graph = structured representation of the problem and environment**  
**Persistent goals = motivational direction**  
**Tools = capabilities for changing or observing the environment**  
**Audit/learning = mechanism for converting experience into future behavior**

The system therefore must not depend on a single LLM or a single prompt.

Conceptually:

    Persistent Goal
          |
          v
    World State / World Model
          |
          v
    Goal Arbitration
          |
          v
    Factor / Causal Graph
          |
          v
    Opportunity + Tool Discovery
          |
          v
    Hypothesis Generation
          |
          v
    Strategy Branching
          |
          v
    Resource Allocation
          |
          v
    Execution
          |
          v
    Observation
          |
          v
    Verification
          |
          v
    Audit
          |
          v
    Learning / Memory / Self-Model
          |
          +---------------------> Graph Reconciliation
                                      |
                                      +--> New Strategy

The loop is persistent.

Design classification: every component is labeled either a **durable complement** (functions a model cannot provide by definition: persistence, authority and security boundaries, budgets, audit trail, actuation, provenance) or an **erodible substitute** (compensates current model weaknesses: planning scaffolds, manual context management, explicit branching). Substitutes live behind ports and must be cheap to remove or reduce to pass-throughs as models improve; complements are permanent.

---

# 3. Goal and Motivation Model

## 3.1 Goal hierarchy

Do not treat every goal as equivalent.

Use the hierarchy:

    META-GOAL
       |
    PERSISTENT GOAL
       |
    OBJECTIVE
       |
    TARGET
       |
    SUB-TARGET
       |
    TASK
       |
    ACTION

Definitions:

### Meta-goal
A very stable principle used to evaluate persistent goals.

### Persistent goal
A long-lived desired state or purpose that generates behavior.

### Objective
A time-bounded or operational interpretation of a persistent goal.

### Target
A measurable desired state.

### Sub-target
A condition, milestone or intermediate state that contributes to a target.

### Task
A concrete unit of work.

### Action
A single executable operation.

The lower levels are disposable. The higher levels are progressively more stable.

Levels are semantic roles, not mandatory layers: a simple goal may instantiate three levels, a complex one seven. What matters is the role semantics (stability decreasing, disposability increasing downward), not the depth of the chain.

---

## 3.2 Goals are generative

A persistent goal must not merely be a parent node containing tasks.

It must continuously generate new candidate behavior.

For each persistent goal, the system asks:

1. What is the current state?
2. What is the desired state?
3. What is the gap?
4. What opportunities currently exist?
5. What new opportunities could exist?
6. What factors support the goal?
7. What factors prevent it?
8. What capabilities are missing?
9. What resources are limiting?
10. Which other goals interact with this goal?
11. Is the current strategy still the best strategy?
12. Are existing sub-goals still necessary?

The system must therefore be capable of discovering a completely new route to the same goal.

---

# 4. Goal Re-evaluation and Strategic Abandonment

The system must continuously verify:

- the ultimate goal;
- every objective;
- every target;
- every sub-target;
- every task;
- every assumption supporting them.

A subordinate goal can be:

- active;
- deferred;
- suspended;
- superseded;
- invalidated;
- completed;
- abandoned.

If a new opportunity changes the relative value of goals, the system must be able to reallocate resources.

Example:

A trip to a mountain was planned.

One week before departure, several business meetings become available and have a significant probability of producing a major improvement toward financial independence.

The system must compare:

    Mountain trip -> contribution to persistent goals
    Meetings     -> contribution to persistent goals

If the meetings have much higher expected marginal value, the mountain branch can be deferred.

The system is not "breaking its plan". It is correctly re-evaluating the plan against the persistent goal.

---

# 5. Goal Arbitration

Every meaningful action should be evaluated against all affected goals, not only the local target.

A conceptual decision value is:

    NetValue(action) =
        ExpectedGoalProgress
      + InformationGain
      + CapabilityGain
      - DirectCost
      - OpportunityCost
      - Risk
      - ResourceConsumption

For multiple goals:

    NetValue(action) =
        sum(
            GoalPriority[i]
            * ExpectedImpact(action, Goal[i])
            * Probability(action, Goal[i])
        )
        - costs
        - risks
        - opportunity cost

The exact scoring function must be configurable and should not be hard-coded into the LLM. The canonical form of the decision-value function is defined in Appendix A.

Sensitivity gate: before committing a significant decision, perturb the low-confidence weights; if the ranking of alternatives flips, the decision is not mature — trigger an information-gain action or escalate.

---

# 6. Marginal Value

Absolute importance is insufficient.

For a candidate action A:

    MarginalValue(A) =
        Value(world | A) - Value(world | not A)

The system should estimate the marginal contribution of:

- actions;
- factors;
- tools;
- resources;
- sub-targets;
- opportunities.

This allows it to prioritize an expensive but critical enabler over a cheap low-impact support.

Example:

- climbing boots: importance 9.9/10;
- energy bars: importance 2/10.

If resources are limited, the system should prioritize boots and find a cheaper substitute for energy bars.

---

# 7. Global Cognitive Graph

The central representation must be a dynamic graph, not only a task tree.

The graph contains at least:

- Goal nodes;
- Objective nodes;
- Target nodes;
- Sub-target nodes;
- Task nodes;
- Action nodes;
- Factor nodes;
- Resource nodes;
- Tool/capability nodes;
- Actor/person nodes;
- Organization nodes;
- Event nodes;
- Evidence nodes;
- Decision nodes;
- Policy nodes;
- Risk nodes;
- Assumption nodes.

Any relevant node may relate to any other relevant node.

Example:

    Goal A: climb mountain
       |
       +-- energy bar --> support +2

    Goal B: diet
       |
       +-- energy bar --> blocker -4

The same entity can therefore support one goal and obstruct another.

---

# 8. Relationship Model

Relationships are first-class objects.

A relationship should contain at least:

    relationship_id
    source_node
    target_node
    relationship_type
    direction
    strength
    importance
    utility
    cost
    probability
    confidence
    risk
    reversibility
    substitutability
    duration
    latency
    dependencies
    side_effects
    causal_evidence
    validation_status
    provenance
    created_at
    updated_at
    validity_status

Relationship types include:

- SUPPORT
- ENABLE
- REQUIRED
- BLOCK
- INHIBIT
- RISK
- ANTAGONIZE
- DEPENDS_ON
- SUBSTITUTES
- AMPLIFIES
- MITIGATES
- CAUSES
- CORRELATES
- DERIVES_FROM
- INVALIDATES
- SUPERSEDES

Deprecated aliases: ENABLES -> ENABLE, OBSTRUCT -> BLOCK. BLOCK prevents progress while present; INHIBIT reduces strength or probability without preventing.

Do not collapse these into one generic positive/negative weight. The normative attribute list and type semantics are defined in Appendix A.

---

# 9. Importance, Utility, Cost and Probability

These dimensions must remain separate.

### Importance
How critical is this relationship/factor to the target?

### Utility
How much benefit does it produce?

### Cost
What resources are required?

### Probability
How likely is the expected effect?

### Risk
How much downside exists?

### Confidence
How reliable is the system's estimate?

### Substitutability
Can another factor provide the same function?

### Reversibility
Can the action be undone?

### Time
How long before the effect appears?

### Opportunity cost
What alternative uses of the same resources are lost?

The LLM may propose values, but structured validators and historical data must calibrate them.

Elicitation discipline:

- prefer ordinal elicitation (critical / high / medium / low) mapped to coarse numeric bands over pseudo-precise decimals;
- prefer pairwise comparisons for cross-goal priorities;
- every estimate carries explicit uncertainty;
- stated precision must never exceed input precision.

---

# 10. Causal and Effect Propagation

The system must distinguish direct effects from indirect effects.

Example:

    Energy bar
       |
       +--> energy
               |
               +--> climbing performance
                       |
                       +--> summit probability
                               |
                               +--> calorie expenditure
                                       |
                                       +--> diet progress

At the same time:

    Energy bar
       |
       +--> calorie intake
               |
               +--> negative diet effect

The system therefore needs effect propagation.

For every important action:

1. calculate direct effects;
2. traverse relevant downstream relationships;
3. calculate secondary and tertiary effects;
4. detect feedback loops;
5. detect effects on other goals;
6. calculate net global effect;
7. record uncertainty.

Do not assume that a locally negative action is globally negative.

Propagation guardrails:

- every causal edge carries a validation status: HYPOTHESIZED, OBSERVED, VALIDATED;
- default propagation depth is 2–3 hops; deeper propagation only along validated chains;
- uncertainty compounds multiplicatively along a path;
- a decision above the impact threshold may not rest on an unvalidated multi-hop chain: validate the weakest link first, or escalate;
- graph hygiene: stale or never-corroborated edges are periodically pruned.

---

# 11. Goal Antagonism

Two goals are antagonistic when an action or state improves one while degrading another.

Represent this explicitly.

Example:

    Goal A --(positive)--> Factor X
    Goal B --(negative)--> Factor X

The system must search for:

1. prioritization;
2. mitigation;
3. substitution;
4. scaling;
5. temporal separation;
6. transformation;
7. a new enabling factor;
8. a new tool.

The system should prefer creating compatibility when economically rational instead of treating every conflict as a binary choice.

---

# 12. Resource Allocation

Resources include:

- money;
- time;
- energy;
- attention;
- computational capacity;
- available agents;
- social capital;
- access;
- tools;
- physical resources;
- information.

Every resource has:

    amount
    availability
    replenishment rate
    opportunity cost
    allocation
    constraints

The system must be able to solve constrained allocation problems.

Conceptually:

    maximize total expected goal value
    subject to:
        budget constraints
        time constraints
        capability constraints
        risk constraints
        dependency constraints

Scaling is allowed.

Example:

10 energy bars may be reduced to 2 if the marginal value after the first two is low.

---

# 13. Opportunity Discovery

The system must continuously search for new opportunities.

Opportunity discovery is distinct from task execution.

For each persistent goal:

    current_state
       |
       v
    gap analysis
       |
       v
    opportunity search
       |
       +--> existing opportunity
       +--> emerging opportunity
       +--> latent opportunity
       +--> capability that could create opportunity

Opportunities should have:

    expected value
    probability
    timing
    cost
    required capabilities
    dependencies
    risks
    expiration
    reversibility

---

# 14. Tool and Capability Discovery

Tools are enablers of goals and targets.

A tool is broader than software.

Possible tools include:

- APIs;
- websites;
- browsers;
- databases;
- code;
- simulations;
- datasets;
- external services;
- human experts;
- organizations;
- suppliers;
- partners;
- financial resources;
- communication channels;
- physical devices;
- skills;
- processes.

For every capability gap:

    What is missing?
       |
       +--> existing tool?
       |
       +--> existing service?
       |
       +--> human resource?
       |
       +--> can be acquired?
       |
       +--> can be built?
       |
       +--> can another tool create it?

If no tool exists, the agent may create a tool, test it and register it in the Tool Graph.

Acquisition security (applies to discovered, imported and self-built tools):

- sandbox-first execution;
- provenance verification;
- least-privilege credentials per tool;
- pinned versions; dependency scanning for built tools;
- promotion to risk class EXTERNAL_COMMUNICATION or higher requires human approval through the Decision Supervisor.

---

# 15. Tool Graph

Tool relationships are also first-class.

Example:

    Tool A
      |
      +--> enables Target A
      +--> obstructs Goal B
      +--> enables Tool B
      +--> requires Resource C
      +--> substitutes Tool D

Each tool must have:

    capability description
    input schema
    output schema
    cost
    latency
    reliability
    permissions
    security classification
    prerequisites
    side effects
    failure modes
    availability
    provenance

---

# 16. Ports and Adapters for External Integrations

Every external integration is defined by a port: a typed, versioned contract owned by this architecture.

    Port (owned contract)
       |
       +--> Adapter A (implementation)
       +--> Adapter B (alternative implementation)
       +--> Mock adapter (testing)

Rules:

- the cognitive core depends only on ports, never on concrete providers;
- each port ships with a mock implementation and a conformance test suite;
- a new adapter must pass the conformance suite in sandbox before production use;
- adapters are swappable behind feature flags;
- where an external API does not match the port, a bridge translates.

Initial ports:

    llm_provider        (the existing provider library integrates as an adapter)
    browser             (agentic browser implementations)
    vault_payments
    voice_call          (CallAPICall integrates later as an adapter; only port + mock initially)
    email
    sms
    identity_2fa
    skill_package       (imported skills)
    mcp_server          (Model Context Protocol client)

This keeps provider choices reversible and lets existing external applications integrate without modifying the core.

---

# 17. Browser / Web Agent

The initial toolset must include an agent-controlled browser.

Support should be designed behind a browser abstraction layer so Chromium-based and Firefox-based implementations can be swapped. The browser is a port in the sense of the Ports and Adapters section: typed contract, mock implementation, conformance suite.

Required capabilities:

- navigate;
- search;
- click;
- type;
- select;
- upload/download where authorized;
- interact with forms;
- handle multiple tabs;
- maintain session state;
- detect login;
- detect consent pages;
- extract structured information;
- submit forms;
- verify completion;
- recover from navigation failures;
- take screenshots;
- produce an action/audit trace.

The browser agent must also recognize CAPTCHA challenges and route them through an authorized solving mechanism or human-in-the-loop flow. Do not hard-code assumptions about one CAPTCHA implementation. CAPTCHA providers and challenge types vary.

The system must not rely on "bypass" logic. It should instead expose:

    CAPTCHA_DETECTED
       |
       +--> authorized automated solver, if legitimately available
       |
       +--> human verification
       |
       +--> abort / defer

The browser tool must expose the resulting status to the controller.

---

# 18. Online Payments and Financial Tools

The architecture must support authorized online payments through a secure financial tool.

Never place raw payment credentials in LLM context.

Use:

    Secure Vault
        |
        +--> payment token / secure handle
        |
        +--> payment method metadata
        |
        +--> authorization policy
        |
        +--> transaction limits
        |
        +--> audit trail

The LLM should receive a capability such as:

    pay(
        merchant,
        amount,
        currency,
        purpose,
        authorization_context
    )

rather than card numbers.

The vault is a port with substitutable provider adapters. Payment flows are designed for strong customer authentication (PSD2/SCA): human confirmation above thresholds is the normal case, not an exception (see Compliance and Privacy).

Payment policy must support:

- per-transaction limits;
- daily/monthly limits;
- merchant restrictions;
- currency restrictions;
- human approval thresholds;
- transaction preview;
- idempotency;
- confirmation;
- reconciliation;
- rollback/refund workflow where supported.

---

# 19. Authentication and 2FA

The system must support authenticated workflows without exposing secrets to the reasoning model.

Architecture:

    Identity Provider
         |
    Authentication Broker
         |
    Session Token / Capability
         |
    Browser Agent

For 2FA:

- support TOTP/authenticator integrations where authorized;
- support OAuth/OpenID Connect;
- support Google authorization where appropriate;
- support human approval;
- support SMS/email-based codes through authorized connectors.

The LLM should receive only the minimum information necessary to continue the workflow.

Authentication secrets must never be written into the audit journal.

---

# 20. SMS and Email

The system must have optional connectors for:

- email reading;
- email sending;
- SMS reading;
- SMS sending where authorized.

These are tools, not memory.

Messages should be converted into structured events:

    MessageEvent
        sender
        recipient
        timestamp
        channel
        subject
        content_reference
        attachments
        extracted_entities
        inferred_intent
        confidence

The controller decides whether the message changes the world state or goal priorities.

---

# 21. Voice and Human Communication

The system must integrate the existing project:

## CallAPICall

CallAPICall provides the voice interaction capability.

Required interface:

    initiate_call()
    answer_call()
    speak()
    listen()
    transcribe()
    detect_speaker_state()
    terminate_call()

Use:

- STT;
- TTS;
- conversation state;
- interruption handling;
- call recording metadata where legally/technically appropriate;
- structured transcript events.

The cognitive architecture should not know implementation details of CallAPICall. It should see a generic communication tool interface.

Initially only the port and a mock implementation are built; the existing application integrates later as an adapter (with a bridge where APIs do not match).

---

# 22. Human Cooperation

Human interaction is not merely an output channel.

The human is another actor in the cognitive graph.

Represent:

    Human
       |
       +--> knowledge
       +--> preferences
       +--> authority
       +--> capabilities
       +--> constraints
       +--> intentions
       +--> commitments
       +--> relationships

The agent must be able to discuss:

- goal importance;
- trade-offs;
- assumptions;
- strategy;
- uncertainty;
- conflicts;
- decisions;
- alternatives;
- reasons;
- resource allocation.

Communication can occur through:

- text;
- email;
- browser forms;
- voice calls;
- other authorized channels.

---

# 23. AI-to-AI Cooperation

The architecture must support discussion with another AI.

Use an Agent Communication Protocol with:

    request_id
    sender_agent
    receiver_agent
    topic
    context_reference
    question
    hypotheses
    evidence
    proposed_actions
    confidence
    disagreement
    response

AI agents should be able to:

- challenge assumptions;
- propose alternatives;
- audit decisions;
- independently research;
- debate strategies;
- provide specialist knowledge;
- act as critics;
- compare forecasts.

Do not automatically trust another AI. Its claims become evidence with provenance and confidence.

---

# 24. Reason / Motivation Model

Understanding "why" is a core requirement.

The system must represent reasons behind:

- human goals;
- AI goals;
- decisions;
- actions;
- preferences;
- objections;
- commitments;
- changes of strategy.

A goal should have a motivation graph.

Example:

    Action
       |
       v
    Immediate objective
       |
       v
    Personal goal
       |
       v
    Persistent goal
       |
       v
    Underlying value / motivation

The system should distinguish:

- stated reason;
- inferred reason;
- evidence;
- confidence;
- alternative explanations.

It must not treat an inferred human motivation as a fact.

---

# 25. Human Motivation Inference

When analyzing a human behavior:

    Observation
       |
       v
    Candidate explanations
       |
       +--> Motivation A
       +--> Motivation B
       +--> Motivation C
       |
       v
    Evidence evaluation
       |
       v
    Confidence distribution

Example:

A person repeatedly delays a task.

Possible explanations:

- low priority;
- insufficient information;
- fear of failure;
- conflicting objective;
- resource shortage;
- strategic waiting;
- lack of motivation.

The system should maintain hypotheses rather than prematurely choosing one.

Motivation hypotheses can influence strategy but must remain explicitly uncertain.

---

# 26. Why Analysis

Every important node and decision should be able to answer:

1. Why does this exist?
2. Why is it important?
3. What does it enable?
4. What depends on it?
5. What happens if it is removed?
6. What alternative exists?
7. Why was this decision made?
8. What evidence supports it?
9. What uncertainty exists?
10. What would invalidate it?

This produces explainable strategic behavior.

---

# 27. Persistent Audit Journal

The journal is the system's authoritative chronological record of experience.

Each important decision creates an event.

Suggested structure:

    decision_id
    timestamp
    agent_id
    goal_context
    state_snapshot_reference
    relevant_factors
    alternatives_considered
    selected_action
    rationale_summary
    expected_outcome
    expected_probability
    constraints
    resources
    predicted_side_effects
    actual_outcome
    outcome_quality
    decision_quality
    errors
    root_cause
    corrective_action
    learned_pattern_reference
    policy_reference
    provenance

Store reasoning summaries and decision-relevant evidence, not unrestricted private chain-of-thought.

The journal is part of the event store, which is the single source of truth for all state (see Event Sourcing, Consistency and Deterministic Replay).

---

# 28. Event Sourcing, Consistency and Deterministic Replay

The event store is the single source of truth.

Rules:

1. Every state change — by the controller, a background worker, or a human through the GUI — is an event appended to the event store.
2. Graph store, memory stores, policy store and GUI views are derived projections, rebuildable from events.
3. Workers are idempotent; concurrent writes use optimistic concurrency (or a single writer per aggregate).
4. Readers use snapshot reads; no reader blocks the writer.
5. Human edits from the GUI are events with provenance human_edit.

Deterministic replay:

    event store + logged LLM inputs/outputs
        |
        v
    faithful re-simulation of any past decision

Replay is required for debugging, audits and regression tests. It must be designed in from the first phase; it cannot be retrofitted.

---

# 29. Audit Engine

Auditing must operate continuously and at multiple time scales.

### Operational audit
Did the action execute correctly?

### Outcome audit
Did it produce the expected result?

### Decision audit
Was the decision rational given the information available at decision time?

### Strategic audit
Was the chosen strategy appropriate?

### Goal audit
Does the target still contribute to the persistent goal?

### Meta audit
Is the architecture's behavior itself producing systematic errors?

The audit engine must be able to interrupt normal execution.

---

# 30. Decision Quality vs Outcome Quality

This distinction is mandatory.

A good decision can produce a bad outcome because of uncertainty.

A bad decision can produce a good outcome by chance.

Therefore store separately:

    DecisionQuality
    OutcomeQuality

Decision quality depends on:

- available information;
- quality of alternatives considered;
- assumptions;
- risk analysis;
- calibration;
- consistency with known policies;
- resource constraints.

Outcome quality depends on:

- actual result;
- progress toward goals;
- side effects;
- cost;
- time.

---

# 31. Decision Abstraction

Concrete decisions must be converted into generalized patterns.

Pipeline:

    Decision Episode
        |
        v
    Context Feature Extraction
        |
        v
    Situation Abstraction
        |
        v
    Causal Pattern
        |
        v
    Policy Candidate
        |
        v
    Validation
        |
        v
    Policy Memory

Example:

Concrete:

    "I bought climbing boots instead of additional energy bars."

Abstract:

    "When resources are constrained, prioritize high-marginal-impact non-substitutable enablers over low-impact substitutable support factors."

This abstraction is reusable in unrelated domains.

---

# 32. Policy Representation

A policy should contain:

    policy_id
    description
    preconditions
    applicable_context
    recommended_behavior
    prohibited_context
    exceptions
    evidence_count
    success_count
    failure_count
    confidence
    expected_value
    known_failure_modes
    provenance
    version
    status

Policy states:

    CANDIDATE
    SHADOW
    ACTIVE
    DEGRADED
    UNDER_REVIEW
    SUPERSEDED
    RETIRED

Policies must evolve rather than becoming immutable rules.

Lifecycle guardrails:

- a policy requires a minimum number of independent supporting episodes before ACTIVE;
- SHADOW mode precedes activation: the policy recommends without acting, and counterfactual agreement with actual decisions is logged;
- default applicability scope is the domain of origin; broadening requires transfer evidence;
- confidence decays if the policy is not reconfirmed (aging);
- conflicts: the more specific policy wins; unresolved conflicts escalate;
- high-use policies are periodically revalidated.

---

# 33. Pattern Matching

Retrieval must not rely solely on vector similarity.

Relevance should combine:

- semantic similarity;
- goal similarity;
- causal similarity;
- constraint similarity;
- factor similarity;
- resource similarity;
- historical success;
- policy applicability.

Conceptually:

    Relevance =
        semantic_similarity
      + causal_similarity
      + goal_similarity
      + constraint_similarity
      + historical_reliability

A semantically similar historical decision may still be causally irrelevant.

The historical_reliability term must come from measured calibration statistics, not from self-assessed confidence.

---

# 34. Counterfactual Analysis

For significant decisions, the system should estimate:

    What happened with A?
    What might have happened with B?
    What might have happened with C?

Counterfactual sources can include:

- simulations;
- historical data;
- alternative branches;
- experiments;
- independent model estimates.

Counterfactuals must be labeled as estimates, not facts.

---

# 35. Memory Architecture

Use multiple storage mechanisms.

## Event Store
Chronological immutable audit history.

## Graph Database
Goals, factors, dependencies, causal relations, conflicts and tool relations.

## Vector Database
Semantic retrieval over documents, experiences and knowledge.

## Structured Database
Metrics, scores, costs, policies, confidence and state.

## Policy Store
Generalized decision rules and learned strategies.

Do not put everything into the vector database.

All stores except the event store are derived projections and must be rebuildable from events. Each store defines retention: TTL/archival classes, consolidation triggers, and controlled forgetting — unbounded growth degrades retrieval precision.

---

# 36. Memory Layers

At minimum:

### Episodic memory
What happened.

### Semantic memory
What the system believes about the world.

### Procedural memory
How to do something.

### Meta-memory
How reliable its own knowledge and retrieval are.

### Policy memory
Which strategies work under which conditions.

### Self-model
How capable/reliable the system is.

---

# 37. Memory Tree / Memory Graph

Memory should be hierarchical and graph-linked.

Example:

    Topic
      |
      +-- concepts
      +-- episodes
      +-- decisions
      +-- errors
      +-- policies
      +-- sources
      +-- contradictions

Retrieval agents should query this structure and return compact reports to the main agent.

The main agent must not load the entire history into context.

---

# 38. Memory Agent

A dedicated background memory agent should:

- index events;
- consolidate experiences;
- detect recurring patterns;
- detect contradictions;
- summarize relevant history;
- update semantic knowledge;
- update policy candidates;
- identify forgotten/underused knowledge;
- identify unreliable sources;
- surface relevant historical failures;
- apply retention policies (TTL, archival, controlled forgetting);
- open work items on detected contradictions rather than leaving them passive;
- measure retrieval quality (precision on real usage).

The main agent asks:

    "What do I need to know about this problem?"

The memory agent responds with a bounded context package.

---

# 39. Context Management

Context is a finite resource.

Use:

- hierarchical summaries;
- references instead of raw history;
- memory retrieval;
- compressed state;
- separate research sessions;
- specialist agents;
- task-specific contexts;
- checkpointed state.

The main agent should receive:

    Current state
    Relevant memory
    Relevant policies
    Relevant graph neighborhood
    Relevant evidence
    Uncertainty summary

rather than the entire historical context.

---

# 40. Research and Knowledge Acquisition

When the system encounters a knowledge gap:

    Knowledge Gap
        |
        v
    Classify gap
        |
        +--> factual
        +--> conceptual
        +--> procedural
        +--> empirical
        +--> computational
        +--> environmental
        |
        v
    Select acquisition method

Methods:

- web research;
- document retrieval;
- RAG;
- expert consultation;
- experiment;
- simulation;
- tool discovery;
- human discussion.

The system must record what was learned and how reliable the source was.

---

# 41. Active Learning

The system should sometimes perform an action primarily because it reduces uncertainty.

Decision value:

    Value(action) =
        GoalProgress
      + InformationGain
      + CapabilityGain
      - Cost
      - Risk

This permits rational experimentation.

The agent can decide:

> "I cannot yet choose between strategies A and B; an experiment costing 2% of the available resources would reduce the uncertainty enough to justify itself."

---

# 42. Hypothesis Engine

The system should not generate only one plan.

For significant decisions:

    Hypothesis A
    Hypothesis B
    Hypothesis C

Each hypothesis contains:

- assumptions;
- supporting factors;
- blockers;
- risks;
- missing factors;
- required tools;
- expected value;
- probability;
- cost;
- reversibility.

The controller evaluates and prunes branches.

Process:

    generate
       |
    test
       |
    score
       |
    prune
       |
    expand promising branches

---

# 43. Strategy Branching

Strategies should form a search tree or DAG.

Branches can be:

- simulated;
- partially executed;
- researched;
- tested;
- abandoned;
- merged.

The system should avoid maintaining unnecessary branches.

Branch lifecycle:

    PROPOSED
      -> TESTING
      -> ACTIVE
      -> DEFERRED
      -> PRUNED
      -> SUCCESSFUL
      -> FAILED

---

# 44. Recovery and Cognitive Version Control

The architecture must support rollback.

When an assumption is found to be false:

    Identify invalid assumption
       |
       v
    Find dependent decisions
       |
       v
    Invalidate downstream state
       |
       v
    Restore last valid checkpoint
       |
       v
    Recalculate
       |
       v
    Generate alternative strategy

This is analogous to version control for cognition.

---

# 45. World Model and Self Model

Maintain two distinct models.

## World Model

What the system believes about the external environment.

## Self Model

What the system believes about its own:

- capabilities;
- limitations;
- reliability;
- calibration;
- tool performance;
- reasoning failure modes;
- biases;
- knowledge gaps;
- resource constraints.

The self-model must be updated by empirical evidence.

---

# 46. Prediction and Calibration

Important decisions should produce explicit predictions.

Before action:

    expected outcome
    probability
    expected time
    expected cost

After action:

    actual outcome
    actual time
    actual cost

Then:

    Prediction Error =
        Expected - Actual

The system should maintain calibration statistics.

Example:

    Domain: software architecture
    calibration: high

    Domain: unfamiliar legal research
    calibration: low

This affects future tool selection and verification requirements.

Calibration is measured with standard metrics (Brier score, Expected Calibration Error), per domain, from the first day of operation.

---

# 47. Meta-Cognitive Audit

The system must periodically inspect its own behavior.

Questions:

- Which types of decisions fail most often?
- Which assumptions are frequently wrong?
- Which tools are overused?
- Which tools are underused?
- Does the system underestimate costs?
- Does it abandon plans too quickly?
- Does it overvalue familiar strategies?
- Does it fail to search for alternatives?
- Does it confuse correlation with causation?
- Does it over-trust sources?
- Does it over-trust other agents?

These observations update the self-model and policies.

---

# 48. Cold Start, Seeding and Earned Autonomy

The learning machinery is empty exactly when the system is most error-prone.

Mitigations:

1. Seed policies: a hand-written starter pack (including the lessons already encoded in the design documents), marked provenance = seed.
2. Curriculum: scenarios run in sandbox/simulation before real-world actions.
3. Apprentice mode: escalation thresholds start high; the controller relaxes them per domain only as measured calibration accumulates.

Autonomy is earned with evidence, never presumed. Budget expansion remains a human decision (see Human Authorization and Bounded Autonomy).

---

# 49. Goal / Graph Reconciliation Cycle

This is the central background process.

Repeatedly:

1. read current world state;
2. read current goal states;
3. update factor states;
4. detect new factors;
5. detect obsolete factors;
6. update relationships;
7. detect conflicts;
8. propagate effects;
9. recalculate goal priorities;
10. identify missing capabilities;
11. discover tools;
12. evaluate opportunities;
13. re-evaluate strategies;
14. prune obsolete branches;
15. generate new branches;
16. reallocate resources;
17. select next actions.

This process must operate continuously, but incrementally: reconciliation is event-driven with dirty-marking — only the subgraph affected by new events is re-evaluated — while full sweeps run only at the macro and meta timescales. Every relevant node carries a review_interval.

---

# 50. Multi-Time-Scale Control

Use at least four control loops.

### Micro loop
Seconds/minutes:
action verification and immediate recovery.

### Meso loop
Hours/days:
task and strategy review.

### Macro loop
Weeks/months:
objective and target review.

### Meta loop
Long-term:
goal structure, learning behavior and self-model review.

Higher loops can invalidate lower-level work.

---

# 51. Controller Responsibilities

The deterministic controller should own:

- lifecycle;
- scheduling;
- state transitions;
- permissions;
- tool invocation;
- audit triggers;
- checkpoints;
- retries;
- branch creation;
- branch pruning;
- context budgets;
- memory retrieval requests;
- policy retrieval;
- resource limits;
- escalation to human;
- escalation to another AI;
- goal reconciliation.

The LLM should propose reasoning outputs; the controller should decide whether and how those outputs become system actions.

The controller executes; the Decision Supervisor independently issues verdicts on significant decisions before execution (see Decision Supervisor).

---

# 52. LLM Interface

LLM calls should be structured.

Input:

    system state
    current goal
    relevant graph neighborhood
    relevant memory
    relevant policies
    available tools
    constraints
    uncertainty

Output should be structured into:

    analysis_summary
    hypotheses
    assumptions
    proposed_plan
    required_tools
    expected_outcomes
    risks
    confidence
    missing_information
    verification_plan

The controller validates the output before execution.

Gateway requirements:

- structured outputs are validated against versioned schemas; on failure: bounded repair loop, then fallback model, then escalation;
- model routing by cost and function: small models for classification/retrieval/extraction, large models for strategic reasoning;
- critics use a different model family from the generator where possible (mitigates correlated errors and multi-agent confirmation);
- all inputs and outputs are logged for deterministic replay;
- costs are accounted per cognitive function.

---

# 53. Tool Execution Contract

Every tool call should produce:

    tool_call_id
    tool
    input_reference
    authorization
    start_time
    end_time
    result_reference
    status
    error
    side_effects
    verification_result

Tools must declare permissions and risk class.

Example risk classes:

    READ_ONLY
    LOW_IMPACT_WRITE
    EXTERNAL_COMMUNICATION
    FINANCIAL
    IDENTITY
    IRREVERSIBLE

High-impact operations should have explicit authorization policies.

Newly acquired tools enter at the most restrictive plausible risk class; promotion requires human approval.

---

# 54. Human Authorization and Bounded Autonomy

Human approval should be configurable by policy rather than hard-coded.

Example:

    payment < €20
        automatic

    payment €20-€500
        automatic if pre-authorized

    payment > €500
        human approval

The same model applies to:

- contracts;
- account changes;
- sensitive communication;
- irreversible actions;
- high-risk external actions.

Bounded autonomy — budgets are first-class resources enforced by the controller and the Decision Supervisor, never by the LLM:

- spend per time window;
- number of external communications per time window;
- irreversible-class actions always require fresh authorization (never batch);
- compute/token budget per goal.

Ratchet principle: budgets expand only by explicit human decision — never through policy learning or a system decision. Budget definitions live in Tier 1 guardrails.

---

# 55. Background Agents

Recommended specialist agents:

### Memory Agent
Retrieval and consolidation.

### Auditor Agent
Past-decision analysis.

### Research Agent
External information acquisition.

### Strategy Agent
Alternative strategy generation.

### Critic Agent
Independent challenge (preferably served by a different model family than the generator).

### Tool Discovery Agent
Searches for new capabilities.

### Goal Analyst
Evaluates goal hierarchy and conflicts.

### Motivation Analyst
Analyzes reasons and motivation hypotheses.

### Simulation Agent
Runs models/counterfactuals.

### Communication Agent
Human and AI interaction.

These agents must not all share the main context.

---

# 56. Auditor Agent and Behavioral Recurrence

The auditor must search historical decisions for analogous behavior.

Pipeline:

    Current decision
       |
       v
    Context abstraction
       |
       v
    Search historical decisions
       |
       v
    Identify behavioral pattern
       |
       v
    Compare outcomes
       |
       v
    Update policy / warning

It must detect:

- repeated success;
- repeated failure;
- recurring mistake;
- recurring bias;
- successful strategy in analogous contexts;
- policy violations;
- unexplained behavioral changes.

---

# 57. Behavioral Pattern Representation

A behavioral pattern should be independent from the exact event.

Example:

    Context:
        limited budget
        multiple competing enablers
        one high-impact non-substitutable resource

    Behavior:
        prioritize high marginal value resource

    Result:
        increased goal probability

    Applicability:
        high

This pattern can later match:

- travel;
- software architecture;
- purchasing;
- project planning;
- business decisions.

---

# 58. Contradiction Management

The graph and memory system must detect:

- contradictory facts;
- conflicting policies;
- inconsistent goals;
- conflicting human instructions;
- outdated assumptions;
- source disagreement.

Do not silently overwrite.

Represent:

    Claim A
    Claim B
    evidence A
    evidence B
    confidence A
    confidence B
    resolution status

Possible statuses:

    UNRESOLVED
    RESOLVED_A
    RESOLVED_B
    CONTEXT_DEPENDENT
    OBSOLETE

---

# 59. Provenance

Every important piece of knowledge must have provenance.

Examples:

- source URL;
- document;
- tool output;
- human statement;
- model inference;
- experiment;
- historical observation;
- another AI.

The system must distinguish:

    observed
    retrieved
    inferred
    hypothesized
    predicted

This is essential for auditing.

---

# 60. State Machine

High-level system states:

    INITIALIZING
    OBSERVING
    PLANNING
    EXECUTING
    VERIFYING
    AUDITING
    LEARNING
    RESEARCHING
    NEGOTIATING
    WAITING
    ESCALATING
    RECOVERING
    REPLANNING
    SUSPENDED

Transitions are controller-owned.

---

# 61. Suggested Core Services

Implement as modular services/interfaces:

    core/
      controller
      goal_engine
      arbitration_engine
      state_manager
      scheduler

    graph/
      graph_store
      causal_engine
      factor_engine
      dependency_engine

    planning/
      planner
      hypothesis_engine
      strategy_engine
      resource_optimizer

    execution/
      executor
      verification
      recovery

    memory/
      event_store
      vector_store
      graph_store
      memory_agent
      consolidation

    learning/
      decision_auditor
      abstraction_engine
      pattern_detector
      policy_engine
      calibration

    cognition/
      llm_gateway
      critic
      self_model
      motivation_engine

    tools/
      tool_registry
      tool_discovery
      skills
      mcp_client
      browser
      web_research
      email
      sms
      payments
      identity
      call_api_call

    collaboration/
      human_interface
      ai_interface
      negotiation
      deliberation

    security/
      vault
      authorization
      guardrails
      decision_supervisor
      taint_tracker
      compliance
      policy_engine
      secrets_manager

    api/
      rest
      websocket
      projections
      commands

    ui/
      web_frontend

---

# 62. GUI and API Layer

The frontend is a browser application, separated from the backend.

Backend:

- API-first: REST for commands and queries, WebSocket/SSE for live events;
- every core component exposes its state and configuration through the API;
- the GUI reads projections and writes commands; every manual change becomes an event with provenance human_edit;
- authorization applies to GUI commands exactly as to system actions.

Required views:

1. Graph explorer: goals, targets, sub-targets, factors, resources, tools; typed relationships (support, required, enabler, blocker, antagonist, ...) with editable weights (importance, cost, probability, ...); every node opens a detail dialog (separate window, dialog or frame) where values can be edited by hand or discussed with the AI (see In-Progress Co-Decision).
2. Guardrail editor: Tier 1 and Tier 2 guardrails with the full flexibility matrix.
3. Goal definition: primary and secondary targets, priorities, motivations.
4. Decision inbox: pending authorizations, supervisor verdicts, overrides.
5. Configuration: LLM providers, tools, ports/adapters, skills, MCP servers, budgets, connectors.
6. Journal, audit and budget dashboards.

Every component must be observable and steerable through the GUI. A component without a GUI surface is incomplete.

---

# 63. Recommended Storage Architecture

A practical first implementation can use:

- PostgreSQL for structured state and events;
- pgvector or a dedicated vector database for semantic retrieval;
- Neo4j or another graph database for graph-heavy workloads;
- object storage for large artifacts;
- Redis for ephemeral queues/cache;
- an event bus for asynchronous agents.

The default first profile is a single PostgreSQL instance: structured state + event store + pgvector for embeddings + recursive CTEs or a graph extension for graph queries + SKIP LOCKED work queues. Additional engines are introduced only when scale demands, behind the same logical interfaces.

The event store is canonical in every profile; the logical separation must remain.

---

# 64. Minimum Data Entities

At minimum implement:

    Goal
    Objective
    Target
    Task
    Action
    Factor
    Resource
    Tool
    Capability
    Relationship
    Decision
    Observation
    Outcome
    Audit
    Error
    Policy
    Hypothesis
    Strategy
    Evidence
    Actor
    Motivation
    MemoryItem
    Checkpoint
    Authorization
    Opportunity
    Guardrail
    SupervisorVerdict
    Budget
    Skill
    McpServer
    DeliberationThread
    ContentTaint

---

# 65. Event Types

Suggested events:

    GOAL_CREATED
    GOAL_UPDATED
    GOAL_REEVALUATED
    TARGET_CREATED
    TARGET_INVALIDATED
    TASK_CREATED
    TASK_COMPLETED
    ACTION_PROPOSED
    ACTION_EXECUTED
    ACTION_FAILED
    OBSERVATION_RECEIVED
    OUTCOME_RECORDED
    AUDIT_STARTED
    AUDIT_COMPLETED
    ERROR_DETECTED
    POLICY_CREATED
    POLICY_UPDATED
    POLICY_RETIRED
    MEMORY_CONSOLIDATED
    TOOL_DISCOVERED
    TOOL_REGISTERED
    TOOL_FAILED
    HYPOTHESIS_CREATED
    HYPOTHESIS_PRUNED
    STRATEGY_CHANGED
    RESOURCE_REALLOCATED
    CONFLICT_DETECTED
    HUMAN_ESCALATION
    AUTHORIZATION_GRANTED
    AUTHORIZATION_DENIED
    GUARDRAIL_CREATED
    GUARDRAIL_UPDATED
    GUARDRAIL_TRIGGERED
    SUPERVISOR_VERDICT
    SUPERVISOR_OVERRIDE
    HUMAN_EDIT
    BUDGET_EXHAUSTED
    INJECTION_SUSPECTED
    SKILL_IMPORTED
    SKILL_RETIRED
    MCP_SERVER_REGISTERED
    MCP_SERVER_DISABLED
    DELIBERATION_OPENED
    DELIBERATION_RESOLVED

Added in revision 1.2 (implemented since 1.1):

    CYCLE_STARTED / CYCLE_COMPLETED / CONTROL_COMMAND / STATE_CHANGED
    CONFIG_UPDATED
    LLM_REQUEST / LLM_RESPONSE / LLM_USAGE
    DECISION_MADE / SENSITIVITY_UNSTABLE
    STRATEGY_PROPOSED / STRATEGY_SELECTED / STRATEGY_UPDATED / STRATEGY_COMPLETED
    TARGET_DEFERRED / TARGET_COMPLETED / OPPORTUNITY_DETECTED
    NODE_ADDED / NODE_UPDATED / NODE_INVALIDATED / EDGE_ADDED / EDGE_UPDATED
    GOAL_PROPOSED / GOAL_RATIFIED
    BUDGET_SET / RESOURCE_SPENT / CONTENT_INGESTED
    VERIFICATION_COMPLETED / POLICY_SHADOW_EVALUATED / CALIBRATION_UPDATED
    CLAIM_RECORDED / CONTRADICTION_DETECTED / CONTRADICTION_UPDATED
    COUNTERFACTUAL_ANALYZED / GRAPH_MAINTENANCE / COMPENSATION_EXECUTED
    DELIBERATION_MESSAGE
    SKILL_UPDATED / MCP_SERVER_UPDATED / TOOL_UPDATED / CAPABILITY_QUARANTINED
    REVIEW_COMPLETED / KNOWLEDGE_ADDED
    DIRECTIVE_ISSUED / FACT_RECORDED
    INTEGRATION_PROPOSED / INTEGRATION_APPLIED / REEVALUATION_REQUESTED

---

# 66. Failure Handling

Every action needs explicit failure semantics.

Failures should be classified:

- transient;
- tool failure;
- authentication;
- authorization;
- knowledge gap;
- wrong assumption;
- planning failure;
- environmental change;
- resource shortage;
- contradictory evidence;
- goal conflict.

For each failure:

    detect
      |
    classify
      |
    diagnose
      |
    recover
      |
    learn
      |
    update policy
      |
    replan

---

# 67. Preventing Infinite Loops

Autonomy requires termination and escalation criteria.

Each loop should have:

- maximum iterations;
- budget;
- time budget;
- uncertainty threshold;
- expected value threshold;
- diminishing-return detector;
- repeated-failure detector.

If no productive progress is possible:

    escalate to human
    or
    suspend
    or
    search for a new strategy

Loop budgets draw from the autonomy budgets defined in Human Authorization and Bounded Autonomy; exhaustion emits BUDGET_EXHAUSTED and suspends the affected goal pending human review.

---

# 68. Anti-Drift Mechanisms

The system must continuously compare:

    current behavior
        vs
    persistent goal

and:

    current sub-goals
        vs
    parent goal contribution

If a sub-goal no longer contributes meaningfully:

    DEFER / ABANDON / REPLACE

The controller must prevent a low-level task from becoming an accidental permanent objective.

---

# 69. Goal Integrity

Persistent goals must have stronger governance than tasks.

A lower-level strategy may be changed freely.

A persistent goal should require stronger evidence/authorization to modify.

The system should distinguish:

    Goal modification
    Goal interpretation
    Goal prioritization
    Strategy modification

These are not the same operation.

Ratification rule: creation, modification, or deletion of meta-goals and persistent goals requires explicit human ratification — the system proposes, the human ratifies (enforced as a Tier 1 guardrail).

Interpretation drift: when the system re-interprets the meaning of a persistent goal, the new interpretation is recorded as an event and periodically reviewed by the human.

Corrigibility: PAUSE, STOP and ROLLBACK commands are honored unconditionally at controller level, never mediated by the LLM; no learned policy may create incentives to resist or delay a human override.

---

# 70. Security Architecture

Security must be external to the LLM.

Never rely on the model to enforce:

- payment limits;
- access control;
- secrets;
- authorization;
- identity;
- irreversible action limits.

Use a policy enforcement layer.

The model requests a capability.

The controller checks:

    Is this tool allowed?
    Is this action allowed?
    Is this actor authorized?
    Is this amount within limits?
    Does this require human approval?

Only then is the tool invoked.

These checks are defined by the two-tier Guardrail System and enforced by the Decision Supervisor (see the following sections); the LLM never carries them.

---

# 71. Two-Tier Guardrail System

Security behavior is governed by guardrails in two tiers.

Tier 1 — Constitution:

- editable only manually by the human, through the GUI;
- the system identity has no write permission at the storage/API level: a technical guarantee, not a convention;
- versioned; every change is an event;
- contains at minimum: goal-ratification rules, corrigibility rules (PAUSE / STOP / ROLLBACK), autonomy budgets, prohibited behavior classes.

Tier 2 — Negotiated guardrails:

- created by the AI/system (typically from audits, incidents or policy learning);
- editable and discussable between human and machine (see In-Progress Co-Decision);
- may never weaken a Tier 1 guardrail; Tier 1 wins every conflict;
- asymmetric activation: a Tier 2 guardrail that RESTRICTS behavior may self-activate immediately; one that EXPANDS permitted behavior requires prior human approval.

Guardrail structure (shares the policy schema, but lives in a distinct store and class):

    guardrail_id
    tier
    description
    behavior_reference        (blocked or allowed behavior)
    flexibility_weight        (hard block | soft block | warn | advisory)
    application_conditions
    exclusions
    exceptions
    provenance
    version
    status

All of it is manageable in the GUI.

---

# 72. Decision Supervisor

A dedicated security component checks the AI's decisions at every level:

    goal creation / modification
    strategy selection
    resource allocation
    tool invocation
    external communication
    payments and irreversible actions

This generalizes the authorization gateway: not only external actions — every significant decision receives a verdict.

Evaluation inputs:

    Tier 1 guardrails
    Tier 2 guardrails
    allowed/blocked behavior lists
    flexibility matrix
    autonomy budgets
    risk class

Verdicts:

    GRANTED
    DENIED
    HUMAN_REQUIRED

Every verdict is an auditable journal event. The human can override any verdict from the GUI, in both directions — approve a denied action, revoke a granted one. Overrides are themselves auditable events and feed the supervisor's own audit: where is it too strict, too permissive, and for which decision classes?

---

# 73. Prompt Injection Defense

The system ingests external text continuously: web pages, emails, SMS, call transcripts, other AIs' messages, tool outputs, tool and skill descriptions. All of it is a potential attack channel.

Doctrine: external content is data, never instructions.

Mechanisms:

1. Provenance tagging on every piece of ingested content.
2. Structural separation of instructions and data in every prompt built by the LLM gateway.
3. Taint tracking: a high-risk action proposed shortly after ingesting external content is treated as potentially injected and requires elevated authorization from the Decision Supervisor (event: INJECTION_SUSPECTED).
4. Imported tool and skill descriptions are untrusted (description poisoning is a known attack on MCP-style ecosystems).
5. Adversarial injection tests are part of the required test suite; resistance is measured, not assumed.

---

# 74. CAPTCHA Handling

The browser subsystem must be flexible because CAPTCHA implementations vary.

Implement a generic challenge interface:

    ChallengeDetected
        provider
        type
        page
        required_action
        status

Supported outcomes:

    SOLVED_AUTOMATICALLY
    SOLVED_BY_HUMAN
    FAILED
    DEFERRED

Do not build the architecture around a single CAPTCHA provider or around brittle challenge-specific assumptions.

---

# 75. Payments, 2FA and Secrets: Context Isolation

Sensitive information must remain outside normal reasoning context.

Use secure handles:

    payment_method_id
    auth_session_id
    mailbox_id
    phone_account_id

The LLM can request an operation against a handle.

The secret-bearing connector executes it.

This greatly reduces leakage risk and makes auditing possible without storing secrets.

---

# 76. Compliance and Privacy

External-world capabilities carry legal obligations. The architecture treats them as constraints enforced by guardrails, not as afterthoughts.

1. AI disclosure: in voice interactions the system discloses that it is an AI (EU AI Act, Art. 50).
2. Recording consent: per-jurisdiction rules resolved before recording or transcription.
3. Personal data (GDPR): the Actor and Motivation models profile natural persons. This requires a lawful basis, data minimization, bounded retention, erasure on request, and no inference of sensitive categories.
4. Honest identity: email, SMS and calls are sent as the system acting on behalf of its principal; impersonation is prohibited.
5. Payments: strong customer authentication (PSD2/SCA) makes human-in-the-loop the normal case above thresholds; the design embraces it.
6. No manipulation: inferred human motivations are never used to manipulate; influence must be transparent (arguments, offers, explicit requests).

---

# 77. Human Escalation

Escalation is a normal cognitive operation, not an exception.

Trigger escalation when:

- uncertainty is too high;
- authorization is required;
- goals conflict beyond policy;
- consequences are irreversible;
- external information cannot resolve uncertainty;
- human preference is required;
- a social negotiation is needed.

The agent should formulate:

    Problem
    Relevant facts
    Alternatives
    Trade-offs
    Recommendation
    Uncertainty
    Exact decision required

This minimizes human cognitive load.

Escalation packets are delivered as deliberation threads in the GUI (see In-Progress Co-Decision): the same surface serves system-initiated escalations and human-initiated challenges.

---

# 78. In-Progress Co-Decision (Deliberation)

Human-AI discussion is a first-class runtime mechanism, not an exception path.

- The human can open any decision, strategy or graph node at any moment and rediscuss it.
- The system answers with the reconstructed rationale from the journal: evidence, alternatives considered, estimates, applied policies.
- The outcome — confirm, modify, cancel — is an event and can trigger replanning.
- The mechanism is bidirectional: escalation packets (see Human Escalation) become deliberation threads in the same GUI.
- Deliberations are stored as episodes and feed auditing and policy learning.

---

# 79. Social and Political Tools

The architecture must treat social/organizational/political mechanisms as possible tools in the abstract sense.

Examples:

- contact a person;
- negotiate;
- form a partnership;
- request information;
- recruit expertise;
- coordinate organizations;
- submit an application;
- change a process;
- acquire authorization.

The system should evaluate them exactly like technical tools:

    cost
    probability
    capability
    time
    dependencies
    risk
    expected goal contribution

---

# 80. Tool Discovery as a Continuous Process

Tool discovery should run in the background.

For active goals:

    Identify capability gaps
       |
       v
    Search tool registry
       |
       v
    Search external ecosystem
       |
       v
    Evaluate candidates
       |
       v
    Test
       |
       v
    Register
       |
       v
    Update goal graph

The system should periodically ask:

> "What could I do now that I could not do previously?"

This is capability expansion.

---

# 81. Skill Acquisition

A repeatedly successful sequence should be promoted into a reusable skill.

Example:

    repeated sequence:
        search website
        authenticate
        fill form
        verify result

becomes:

    Skill: submit_authorized_web_application

Skills should contain:

- preconditions;
- steps;
- tools;
- failure modes;
- verification;
- confidence;
- version;
- applicable domains.

---

# 82. Imported Skills and MCP Servers

Capabilities must be importable as packaged extensions, in the manner of modern agent runtimes (e.g., Claude Code, Hermes).

Skill packages:

- self-contained procedural knowledge: manifest (name, description, applicability triggers, risk class, version, provenance) + instructions + optional scripts/resources;
- imported skills register into procedural/policy memory with provenance imported (distinct from skills learned through Skill Acquisition);
- loaded on demand (progressive disclosure) to respect context budgets.

MCP servers (Model Context Protocol):

- the tool registry acts as an MCP client;
- on import: enumerate the server's tools and resources -> map them into Tool Graph nodes with schemas and cost/latency/reliability estimates -> assign risk classes -> run conformance tests in sandbox -> register;
- an MCP server is one adapter type behind the tool ports.

Security (applies to both):

- sandbox-first execution; provenance verification; least-privilege credentials per integration;
- promotion to risk class EXTERNAL_COMMUNICATION or higher requires human approval through the Decision Supervisor;
- descriptions and outputs are untrusted content (see Prompt Injection Defense);
- versions are pinned; an update re-triggers validation.

Management:

- import, enable/disable, inspect and permission skills and MCP servers from the configuration GUI;
- tool discovery includes skill/MCP registries as first-class acquisition channels.

---

# 83. Architecture of a Single Decision Cycle

For every important decision:

    1. Load persistent goals
    2. Load current objectives
    3. Read current state
    4. Retrieve relevant memory
    5. Retrieve relevant policies
    6. Inspect graph neighborhood
    7. Identify conflicts
    8. Identify missing information
    9. Identify missing tools
    10. Generate hypotheses
    11. Generate strategies
    12. Estimate effects
    13. Estimate costs
    14. Estimate opportunity costs
    15. Evaluate alternatives
    16. Select strategy
    17. Create checkpoint
    18. Execute
    19. Observe
    20. Verify
    21. Audit
    22. Learn
    23. Update graph
    24. Re-evaluate goals
    25. Continue / replan / defer / abandon

---

# 84. Continuous Background Processes

Recommended background workers:

    Goal Reconciliation Worker
    Audit Worker
    Memory Consolidation Worker
    Policy Learning Worker
    Tool Discovery Worker
    Opportunity Discovery Worker
    Calibration Worker
    Contradiction Worker
    Self-Model Worker
    Graph Maintenance Worker

These workers should operate independently from the main execution loop.

---

# 85. Implementation Phases

Phases are vertical slices: each phase must end with the complete loop running on a richer scenario than the previous one, with an executable acceptance scenario and its GUI slice. Never build horizontal infrastructure without closing the loop.

## Phase 0 — Minimum Viable Loop

Implement the complete loop end-to-end on a toy domain:

    goal -> reconciliation -> planning -> action (2 tools)
         -> verification -> journal -> audit -> policy candidate

Single process; single PostgreSQL; API-first backend with a minimal GUI (graph viewer + decision inbox); minimal Tier 1 guardrails and Decision Supervisor.

Goal: the loop closes, and every later phase grows a working system.

## Phase 1 — Core engine

Implement:

- controller;
- state manager;
- persistent goals;
- targets/tasks/actions;
- event journal;
- basic LLM gateway;
- basic tool registry.

Goal: deterministic execution and complete auditing.

## Phase 2 — Graph

Implement:

- graph storage;
- factors;
- relationships;
- weights;
- conflicts;
- dependency propagation.

Goal: global state representation.

## Phase 3 — Planning and arbitration

Implement:

- hypothesis generation;
- branching;
- goal arbitration;
- resource allocation;
- opportunity cost;
- dynamic reprioritization.

Goal: strategic autonomy.

## Phase 4 — Memory and learning

Implement:

- episodic memory;
- semantic memory;
- procedural memory;
- decision abstraction;
- policy engine;
- calibration;
- counterfactual evaluation.

Goal: experience accumulation.

## Phase 5 — Tool ecosystem

Integrate:

- browser;
- web research;
- email;
- SMS;
- identity;
- payment vault;
- 2FA;
- CallAPICall.

Goal: environmental autonomy.

## Phase 6 — Meta-cognition

Implement:

- self-model;
- bias detection;
- recurring behavior detection;
- contradiction management;
- policy evolution.

Goal: adaptive self-improvement.

## Phase 7 — Persistent autonomous operation

Implement:

- background workers;
- multi-timescale audits;
- opportunity discovery;
- capability discovery;
- long-running goal management;
- human escalation.

Goal: long-horizon autonomous operation.

---

# 86. Acceptance Criteria

The system is not considered complete merely because it can execute tasks.

It must demonstrate:

### Goal autonomy
It can derive subordinate goals from a persistent goal.

### Goal re-evaluation
It can abandon/defer obsolete sub-goals.

### Conflict management
It can detect when one factor supports one goal and harms another.

### Causal propagation
It can reason about indirect effects.

### Resource optimization
It can trade off cost against importance.

### Opportunity cost
It can recognize that choosing one action consumes an alternative opportunity.

### Tool discovery
It can identify missing capabilities and search for tools.

### Experience learning
It can abstract past decisions into reusable policies.

### Behavioral recurrence
It can detect that a current situation resembles previous successful/failed behavior.

### Decision auditing
It distinguishes decision quality from outcome quality.

### Memory
It retrieves relevant experience without filling the main context with history.

### Self-model
It learns where its predictions are reliable or unreliable.

### Human collaboration
It can ask for and discuss strategic decisions.

### AI collaboration
It can obtain independent critiques.

### Motivation analysis
It can represent and reason about why goals/actions exist.

### Persistent operation
It can continue working toward a goal without being handed a new task at every step.

---

# 87. What This System Is Not

It is not:

- a chatbot;
- a single prompt;
- a simple ReAct loop;
- a task queue;
- a vector database with an LLM;
- a static planner;
- a fixed workflow;
- a collection of independent agents.

Those components may exist inside the system, but they are not the architecture.

---

# 88. Target Architectural Property

The desired behavior is:

    "I have a persistent purpose.
     I understand my current state.
     I know what prevents or enables progress.
     I know what resources and tools I have.
     I can discover new tools.
     I can generate multiple strategies.
     I can estimate consequences.
     I can act.
     I can observe what happened.
     I can audit whether my decision was good.
     I can learn from the result.
     I can recognize the same pattern later.
     I can modify my future behavior.
     I can discover that my current target is no longer useful.
     I can discover a better opportunity.
     I can change strategy.
     I can ask a human or another AI when needed.
     I can continue."

That behavioral loop is the target.

---

# 89. Final Architectural Definition

The complete system can be described as:

    Persistent Goals
        +
    Dynamic Goal Arbitration
        +
    World/State Model
        +
    Causal Factor Graph
        +
    Resource Optimization
        +
    Opportunity Discovery
        +
    Tool/Capability Discovery
        +
    Hypothesis Generation
        +
    Strategy Branching
        +
    Execution
        +
    Observation
        +
    Verification
        +
    Persistent Audit Journal
        +
    Decision Abstraction
        +
    Policy Learning
        +
    Episodic/Semantic/Procedural/Meta Memory
        +
    Self Model
        +
    Motivation Model
        +
    Human/AI Collaboration
        +
    Continuous Reconciliation

The system should therefore be implemented as a **persistent, recursive, goal-directed cognitive control architecture**.

The LLM is the reasoning substrate.

The controller is the executive mechanism.

The graph is the structured model of goals, causes, dependencies and capabilities.

The memory is the accumulated experience.

The audit system converts behavior into measurable learning.

The tool layer connects cognition to the external world.

The persistent goal provides direction.

The defining property is not merely intelligence at one inference step, but the ability to **continuously transform experience into better future decisions while maintaining alignment with persistent goals and dynamically reconstructing the path toward them**.

---

# 90. Immediate Cloud Code Deliverables

Cloud Code should implement the project in this order:

1. Create repository/module structure.
2. Implement domain entities and event model.
3. Implement persistent goal hierarchy.
4. Implement deterministic controller/state machine.
5. Implement event journal.
6. Implement graph abstraction and relationship model.
7. Implement factor scoring and effect propagation.
8. Implement goal arbitration.
9. Implement resource/cost/opportunity-cost evaluation.
10. Implement hypothesis and strategy branching.
11. Implement tool registry and capability model.
12. Implement tool discovery interface.
13. Implement LLM gateway with structured outputs.
14. Implement execution/verification/recovery.
15. Implement audit engine.
16. Implement decision abstraction.
17. Implement policy store and policy evaluation.
18. Implement memory layers and retrieval agent.
19. Implement calibration and self-model.
20. Implement motivation/reason model.
21. Implement background workers.
22. Integrate browser automation.
23. Integrate secure vault and payment capability.
24. Integrate authentication/2FA connectors.
25. Integrate email and SMS.
26. Integrate CallAPICall.
27. Implement human escalation and AI-to-AI communication.
28. Implement observability, metrics and replay.
29. Implement long-running autonomous test scenarios.
30. Validate against the acceptance criteria above.
31. Implement the two-tier guardrail system (Tier 1 storage-enforced).
32. Implement the Decision Supervisor with GUI override.
33. Implement the API layer and web GUI (graph explorer, guardrail editor, decision inbox, configuration, dashboards).
34. Implement deliberation threads (in-progress co-decision).
35. Implement skill-package import and the MCP client integration.
36. Implement the compliance layer (AI disclosure, consent, personal-data handling for actor/motivation models).

The numbered list is the component inventory, not the build order: execution follows the phase plan (Phase 0 first, then vertical slices).

---

# 91. Non-Negotiable Design Decisions

The following decisions should not be silently changed during implementation:

1. Persistent goals are above task-level plans.
2. Sub-goals are provisional and can be abandoned.
3. The system must continuously re-evaluate the ultimate goal and all descendants.
4. The graph is global rather than a collection of isolated task trees.
5. Relationships are weighted and multi-dimensional.
6. Factors can support one goal and obstruct another.
7. Direct and indirect effects must be considered.
8. Cost and opportunity cost are first-class.
9. Tool discovery is part of cognition.
10. Tools include software, people, organizations, resources and capabilities.
11. The system must be able to create new tools/skills when appropriate.
12. Decisions and outcomes must be audited separately.
13. Concrete decisions must be abstracted into reusable patterns.
14. Policies must be conditional, versioned and retractable.
15. Memory is multi-layered; a vector database alone is insufficient.
16. Context must be actively managed.
17. A self-model must track capability and calibration.
18. Human and AI collaboration are first-class capabilities.
19. Motivation/reason analysis is part of the cognitive model.
20. High-impact external actions are controlled by an authorization layer, not by the LLM.
21. Secrets never enter normal LLM context or audit logs.
22. Browser automation must be provider-agnostic and capable of human escalation for challenges such as CAPTCHA.
23. Payments must use secure handles/vaults rather than raw credentials.
24. Every meaningful external action must produce an auditable event.
25. The controller, not the LLM, owns lifecycle, permissions and state transitions.
26. Meta-goals and persistent goals are created, modified or deleted only with explicit human ratification; the system proposes.
27. PAUSE, STOP and ROLLBACK are honored unconditionally at controller level; no learned policy may create incentives to resist or delay human override.
28. External content (web, email, transcripts, other AIs, tool and skill descriptions) is data, never instructions; high-impact actions influenced by recently ingested external content require elevated authorization.
29. Autonomy budgets are hard-enforced by the controller and expand only by human decision (ratchet), never through learning.
30. Tier 1 guardrails are technically non-writable by the system identity; Tier 2 guardrails may self-activate only in the restrictive direction — permissive changes require prior human approval.
31. Every significant decision passes the Decision Supervisor and produces an auditable verdict event; human override is always available via GUI, in both directions.
32. All writes flow through the event store (single source of truth); any decision must be reconstructable via deterministic replay (events + logged LLM I/O).
33. Every external integration (LLM providers, browser, vault, voice, email/SMS, skills, MCP servers) sits behind a typed port with substitutable adapters, sandbox-first validation and conformance tests.

---

# 92. Definition of Done

The list below is the north star, not a completion gate. Progress is tracked against verifiable milestones, each of independent value:

    M0  Phase 0 loop closed on a toy domain
    M1  persistent multi-goal operation with guardrails, supervisor and GUI on simulated scenarios
    M2  memory and learning measurably reduce repeated errors (error-recurrence metric)
    M3  tool/skill/MCP acquisition works end-to-end under sandbox policy
    M4  long-horizon autonomous operation with human oversight in production domains

The north star: the project approaches completion when a persistent goal can be supplied and the system can autonomously:

- understand the goal and its motivation;
- construct a dynamic goal/factor/resource/tool graph;
- identify missing conditions;
- discover opportunities;
- discover or create tools;
- generate competing strategies;
- evaluate costs and opportunity costs;
- resolve cross-goal conflicts;
- execute actions;
- interact with websites and authorized external systems;
- communicate with humans by text and voice;
- cooperate with other AIs;
- observe and verify outcomes;
- audit decisions;
- identify recurring behavioral patterns;
- convert successful/failed experience into policies;
- retrieve relevant policies later;
- update its self-model;
- revise or abandon obsolete sub-goals;
- replan when the environment changes;
- preserve the persistent goal while dynamically changing the route toward it;
- continue operating over long time horizons without requiring a new human prompt for every step.

The system should be judged primarily by **long-horizon autonomous goal achievement, adaptability, calibration, learning from experience, and quality of strategic decisions**, not by isolated benchmark performance of the underlying LLM.
---

# 93. Cross-AI Review (M29)

A second, independent AI reviews the primary's sensitive outputs
before they are enacted. The reviewer is any adapter behind the LLM
port (§16, §49) running behind its own gateway instance, so every
exchange is logged (`LLM_REQUEST/RESPONSE/USAGE`), deterministic in
replay, and cost-accounted per role. In production the reviewer should
be a different provider or model family from the primary (mitigating
the multi-agent confirmation failure mode).

**Review matrix (normative).** Configuration holds one policy per
checkpoint, runtime-editable by the human only (`CONFIG_UPDATED`):

    review_matrix: {
      <checkpoint>: { enabled: bool,
                      max_rounds: int,          # interactions allowed to reach consensus
                      on_disagreement: "human" | "primary_decides",
                      min_risk_class?: str }    # decision checkpoint only
    }

Checkpoints: `decision` (every significant decision at or above
`min_risk_class`, i.e. the enactment of actions), `strategy` (the
setting and management of subtargets: strategy branches, §before
selection guides arbitration), `retrospective` (the regressive
analyses: audit §29–30 + counterfactual §34), `integration` (exogenous
weaving proposals, §95).

**Consensus protocol.** Mechanics are deterministic; only the wording
is generative. Per round: the reviewer's `review` role returns
objections (an empty set = agreement); the primary's `defend` role
returns maintained points with evidence — an empty set means the
primary **concedes** and the subject is **withdrawn** (a conceded
decision is pruned and never enacted). Outcomes:

- `consensus` — proceed; agreed points accumulate per checkpoint;
- `withdrawn` — not enacted;
- rounds exhausted → the matrix override decides:
  - `"human"`: the final decision is discussed with the human before
    being enacted — a decision's verdict is forced to HUMAN_REQUIRED
    with the standing objections as `[review]` reasons (§72); a
    strategy branch defers, a system deliberation thread opens (§78)
    and replanning pauses until it is resolved; a contested
    retrospective opens a thread and its audit must not feed policy
    learning (§31–32) until then;
  - `"primary_decides"`: the primary's `decide` role rules, and MUST
    receive the consensus points already agreed for that checkpoint;
    the dissent stays on record as a verdict advisory and in the
    review record.

Every review is one auditable `REVIEW_COMPLETED` event attached to its
journal record (§27) and rendered in the deliberation surface.

---

# 94. Grounding Check (M30)

An anti-hallucination layer *inside* the guardrail system (§71): a
guardrail rule kind, optional and carrying the full flexibility matrix
(hard/soft block, warn, advisory; conditions, exclusions, exceptions;
Tier 1 or 2):

    { kind: "ground_check", attributes: [..],
      tolerance: float, require_evidence?: bool }

**Knowledge store.** A deterministic local retrieval store with two
inflows only: the system's own **observations auto-index** (research
results — the world is the best ground truth), and the human adds
curated documents (`KNOWLEDGE_ADDED`, human-only — the system must not
launder self-asserted facts into its own ground truth). The reference
retrieval is lexical and dependency-free; an embedding retriever may
replace it behind the same interface without touching callers.

**The check runs with no LLM in the loop.** A decision whose claimed
value for a listed attribute contradicts the grounded value beyond
`tolerance` triggers the guardrail deterministically;
`require_evidence` additionally flags confident claims with no
grounding at all. This is defense in depth with the prompt-injection
taint (§73): the adversarial advert's fake price is caught by
contradiction even where the taint window has been ablated.

---

# 95. Exogenous Inputs: Directives and Facts (M31)

Human decisions and world changes enter the *running* loop as
first-class weighted graph nodes.

**Node kinds (normative).**

- `DIRECTIVE` — a normative human decision issued mid-flight: a new
  short/long-horizon target, an imposed limit or thing to avoid, a
  context change. Weight = `priority`; props `horizon`
  (short|long), `directive_type` (target|constraint|context),
  `description`. **DIRECTIVE is a member of GOAL_KINDS**: an ACTIVE
  directive is a propagation anchor, weighed automatically by causal
  propagation (§10), arbitration U(a) (§5, A.3), antagonism analysis
  (§11) and critique among all existing decision points.
- `FACT` — a descriptive scenario change: `imposed` (true on arrival —
  a law, an inheritance) or an `opportunity` the human accepts or
  declines. Weight = `importance`. Facts are not anchors; they act
  through their typed edges and the blocking rule below.

**Origin envelope (normative, federation-ready).** Every exogenous
node carries `origin: {source, authority, instance}`. Only
`authority: "owner"` (the local human) is trusted. Any other authority
is external content: `CONTENT_INGESTED` + taint (§73), ground-check
applicable (§94), consensus always required, never auto-active, never
Tier 1. Future superior/peer AI instances (see
`docs/future_features.md`) enter through this same channel with a
different envelope — the network is not a new trust boundary.

**Integration = consensus before weaving.** On creation
(`DIRECTIVE_ISSUED` / `FACT_RECORDED`), the gateway role `integrate`
proposes: typed weighted edges against the existing graph ("avoid X" →
BLOCK), new plan subtargets, deferrals, budget impacts, detected
conflicts, open questions (`INTEGRATION_PROPOSED`). The proposal —
optionally after cross-AI review (§93, checkpoint `integration`) —
opens a system deliberation thread (§78). Resolving it
confirmed/modified applies it (`INTEGRATION_APPLIED`) with human
provenance: edges VALIDATED (`integration_agreed:<id>`), spawned
targets created and ratified by that explicit human confirmation (goal
governance §69 intact), deferrals applied, the node ACTIVE. Budget
impacts are NEVER applied automatically (the autonomy ratchet):
they are listed for the human as change-set operations (§96). Below a
configurable weight threshold, edges may self-apply as HYPOTHESIZED
under the causal-graph guardrails (§10); opportunities and non-owner
inputs never auto-weave.

**Deterministic reversible blocking.** A TARGET/SUB_TARGET with an
active BLOCK/INHIBIT edge from an ACTIVE directive/fact is deferred by
the reconciler (with a `deferred_by` marker) and MUST reactivate when
the blocker ceases to be active — imposed limits dissolve when
retired.

**CRUD with re-evaluation (normative).** Updates emit `HUMAN_EDIT` +
`REEVALUATION_REQUESTED` and dirty the subgraph for the event-driven
reconciler; a re-integrate command re-runs the weaving analysis in a
fresh thread. Deletion is event-sourced retirement: the node and every
touching edge are invalidated, integration-spawned nodes are listed in
an orphan-review thread for the human, and blocked targets reactivate.

---

# 96. Extended Human–AI Interaction (M32)

Extends deliberation (§78) in both directions.

**Change-set resolutions.** A thread resolution of outcome `modified`
may carry a typed operation list, each op routed through its existing
human-identity channel — no new authority is created:

    { op: "node_props" | "new_directive" | "new_fact"
        | "propose_goal" (+ ratify) | "defer_target"
        | "set_budget" | "create_guardrail", ... }

Any conversation can therefore, on the human's request, modify the
overall scenario and targets, transactionally recorded in the
resolution's effects.

**Scenario threads.** Subject kind `scenario`: the evidence packet is
the whole picture (active goals, open/deferred targets, budget, active
directives and facts), so the human can discuss the overall course and
close with a change-set.

**AI-initiated consultations.** Beyond escalations (§77), review
disagreements (§93) and integrations (§95), the system opens a
consultation thread when a detected conflict (§11) touches a human
DIRECTIVE — the trade-off is the human's to weigh — and, config-gated
(`consultation_interval_cycles`, default off), a periodic sync thread
summarizing state and open questions.

---

# 97. Feature Settings Surface (M33)

Every optional mechanism above is operable without editing raw
configuration: the GUI (§62) exposes structured panels — the cross-AI
review matrix per checkpoint (enable, max rounds, disagreement
override, minimum risk class), grounding (list/toggle/create
ground-check guardrails, knowledge-store size), and the exogenous /
consultation knobs (consensus requirement, auto-weave threshold,
consultation cadence). All writes go through the existing human-only
configuration and guardrail APIs and are auditable `CONFIG_UPDATED` /
guardrail events; the raw configuration table remains as the power
fallback.

---

# Appendix A. Canonical Schema (Normative)

This appendix is the single normative definition shared by the three PGDCA documents (paper, design rationale, implementation specification). Where any section or document diverges, this appendix wins.

## A.1 Relationship attributes

    relationship_id
    source_node
    target_node
    relationship_type
    direction
    strength
    importance
    utility
    cost
    probability
    confidence
    risk
    substitutability
    reversibility
    latency
    duration
    dependencies
    side_effects
    causal_evidence
    validation_status      (HYPOTHESIZED | OBSERVED | VALIDATED)
    provenance
    created_at
    updated_at
    validity_status        (lifecycle: active | deferred | invalidated | superseded)

## A.2 Relationship types

    SUPPORT       increases the probability or quality of the target
    ENABLE        makes the target possible (weaker than REQUIRED)
    REQUIRED      the target cannot be achieved without it
    BLOCK         prevents progress while present
    INHIBIT       reduces strength or probability without preventing
    RISK          introduces potential downside
    ANTAGONIZE    helps one goal while harming another
    DEPENDS_ON    ordering / prerequisite dependency
    SUBSTITUTES   can provide the same function as another node
    AMPLIFIES     increases the effect of another relationship or factor
    MITIGATES     reduces a risk or a negative effect
    CAUSES        causal production of an effect
    CORRELATES    statistical association without established causation
    DERIVES_FROM  provenance / derivation link
    INVALIDATES   renders another node or assumption invalid
    SUPERSEDES    replaces another node, strategy or policy

Deprecated aliases: ENABLES -> ENABLE, OBSTRUCT -> BLOCK.

## A.3 Canonical decision-value function

    U(a) = sum_i [ w_i * p_i(a) * dV_i(a) ]
           - C(a) - R(a) - OC(a)
           + IG(a) + CG(a)

    w_i     = current priority of goal i
    p_i(a)  = probability that a produces its expected impact on goal i
    dV_i(a) = expected marginal contribution of a to goal i
    C(a)    = direct cost
    R(a)    = risk-adjusted cost
    OC(a)   = opportunity cost
    IG(a)   = expected information gain
    CG(a)   = expected capability gain

The linear-additive form is a configurable default, not a theoretical commitment; alternative aggregations (non-additive interactions, risk attitudes) may replace it per domain. The stated precision of U(a) must never exceed the precision of its inputs.

## A.4 Phase plan

The normative implementation plan is the Implementation Phases section of this specification (Phase 0 upward, vertical slices). The paper's research program and the rationale's implementation dependency order are descriptive and defer to it.
