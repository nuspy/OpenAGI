# PGDCA — Cognitive Architecture & Design Rationale

**Persistent Goal-Directed Cognitive Architecture (PGDCA)**  
**Design Rationale, Architectural Genesis and Implementation Context**  
Version 1.1 — 30 August 2026

> Revision 1.1 applies the approved modifications recorded in `ANALISI_E_PROPOSTE.md` (goal governance, injection defense, bounded autonomy, two-tier guardrails, decision supervisor, GUI, interface-first tooling, imported skills/MCP, vertical-slice phasing). Section numbering shifted with the inserted sections.

---

## 0. Purpose of This Document

This document is intended primarily for **Claude Code and other implementation agents** working on PGDCA.

It is not a scientific paper and it is not merely an implementation checklist.

Its purpose is to preserve the **reasoning, discoveries, architectural decisions, assumptions, and motivations** that led to PGDCA so that implementation agents understand not only **what must be built**, but **why it must be built that way**.

This distinction is critical.

A coding agent that receives only a component list can easily simplify the architecture into conventional:

> prompt → LLM → tool → result

or:

> goal → task tree → executor.

That is explicitly **not** the architecture being designed.

PGDCA is intended to be a persistent cognitive system in which an LLM is one generative component inside a deterministic executive process.

The implementation agent must therefore preserve the architectural principles in this document even when choosing concrete technologies, databases, frameworks, model providers, or implementation strategies.

---

# 1. Executive Summary

PGDCA is based on the following central hypothesis:

> **Once a general-purpose foundation model has sufficient broad cognitive competence, a substantial portion of the remaining gap toward AGI can be addressed at the system-architecture level rather than exclusively by increasing model intelligence.**

The model provides generative intelligence.

The architecture provides:

- persistence;
- temporal continuity;
- goals;
- motivation;
- memory;
- world state;
- causal relationships;
- planning;
- strategy branching;
- verification;
- auditing;
- experience abstraction;
- policy learning;
- resource allocation;
- tool discovery;
- capability acquisition;
- multi-goal arbitration;
- human cooperation;
- AI cooperation;
- self-modeling;
- continual replanning.

The system is therefore not conceived as a single intelligent model.

It is conceived as:

> **a deterministic orchestration mechanism that repeatedly invokes generative intelligence as part of a persistent closed-loop cognitive process.**

The deterministic controller does not make the LLM deterministic.

It determines:

- when reasoning occurs;
- what state is exposed;
- which memory is retrieved;
- which tools are available;
- which hypotheses are investigated;
- when critique is required;
- when execution is authorized;
- when verification is required;
- when auditing occurs;
- when experience is abstracted;
- when strategies are changed;
- when goals are reprioritized;
- when obsolete sub-goals are deleted;
- when new capabilities must be acquired.

---

# 2. The Fundamental Observation That Led to PGDCA

The project originated from a specific observation about current LLMs.

Modern foundation models already exhibit broad competence across many domains.

Even models that are not among the very best benchmark performers can often:

- understand natural language;
- write software;
- analyze software;
- explain scientific concepts;
- perform mathematical reasoning;
- synthesize information;
- research unfamiliar subjects;
- generate plans;
- interpret documents;
- use tools;
- reason across multiple domains.

A single model can therefore possess knowledge and reasoning capabilities spanning many fields.

This creates an important distinction.

The problem is increasingly less:

> "How do we make the model know how to do one more thing?"

and increasingly:

> "How do we make the existing intelligence persistently operate toward objectives in an open-ended environment?"

This is the conceptual starting point of PGDCA.

---

# 3. Model Intelligence vs System Intelligence

PGDCA deliberately distinguishes two levels.

## 3.1 Model Intelligence

Model intelligence is the capability available during one inference operation.

Conceptually:

```text
context
   ↓
LLM
   ↓
generated reasoning / answer
```

This computation is bounded by:

- context;
- available information;
- prompt construction;
- model capability;
- inference budget.

The model may be extremely capable while still being effectively stateless between independent interactions.

---

## 3.2 System Intelligence

System intelligence emerges when the model is embedded inside a persistent feedback loop.

```text
goal
 ↓
state
 ↓
memory
 ↓
reasoning
 ↓
action
 ↓
observation
 ↓
verification
 ↓
audit
 ↓
learning
 ↓
policy update
 ↓
new state
 ↓
new reasoning
```

The system can therefore accumulate consequences over time.

The key property is **temporal continuity**.

The intelligence is no longer only:

> "What can the model answer now?"

It becomes:

> "What can the system accomplish over a long sequence of decisions while remembering, learning, adapting and continuing to pursue its objectives?"

---

# 4. Why a Conventional Agent Is Not Enough

A conventional agent often looks like:

```text
User request
    ↓
LLM
    ↓
Plan
    ↓
Tool
    ↓
Result
    ↓
LLM
```

This solves an important problem: it allows the model to act.

But it does not automatically solve:

- persistent motivation;
- long-term goals;
- cross-goal conflicts;
- strategic memory;
- systematic auditing;
- policy abstraction;
- capability acquisition;
- continuous opportunity discovery;
- changing objectives;
- causal propagation between goals;
- resource allocation across competing objectives;
- self-modeling.

A task-oriented agent is still fundamentally task-oriented.

PGDCA is **goal-oriented and continuously state-oriented**.

---

# 5. The Motivational Layer

A fundamental decision is that the system must begin from **goals**, not tasks.

Humans do not normally execute an arbitrary infinite sequence of tasks without a reason.

A person acts because something is desired.

For example:

```text
Persistent life goal
    ↓
Financial independence
    ↓
Economic objectives
    ↓
Career / business strategies
    ↓
Projects
    ↓
Tasks
    ↓
Actions
```

The action is therefore the bottom of a hierarchy whose origin is a desired future state.

PGDCA reproduces this structure explicitly.

---

# 6. Goal Hierarchy

The canonical hierarchy is:

```text
META-GOAL
   ↓
PERSISTENT GOAL
   ↓
OBJECTIVE
   ↓
TARGET
   ↓
SUB-TARGET
   ↓
TASK
   ↓
ACTION
```

However, this is not a rigid tree.

A sub-target is a **hypothesis about how to reach a higher-level target**.

Therefore:

> A sub-target can become invalid.

For example:

```text
Goal:
Reach financial independence

Sub-goal:
Acquire certification

Later:
A different opportunity makes the certification unnecessary.

Result:
Certification sub-goal should be removed.
```

The system must therefore continuously verify whether every node is still justified by its parent objective.

The seven levels are semantic roles, not mandatory layers: hierarchies have variable depth, and a simple goal does not need seven bureaucratic strata. What matters is the role semantics — stability decreasing and disposability increasing downward.

---

# 7. Goal Reconciliation

At every significant cognitive cycle, the system must ask:

1. Is the ultimate goal still valid?
2. Is its priority still correct?
3. Are its assumptions still valid?
4. Are its sub-goals still necessary?
5. Has the environment changed?
6. Has a new opportunity appeared?
7. Has a blocker disappeared?
8. Has a cheaper path appeared?
9. Has another goal become more important?
10. Is the current strategy still the best available strategy?

This process is **Goal Reconciliation**.

It prevents the system from blindly executing plans that were correct when created but became irrational later.

---

# 8. The Mountain Example

Consider:

> Reach the summit of a mountain.

Possible supporting factors:

- climbing boots;
- ice axe;
- helmet;
- warm clothing;
- food;
- energy bars.

Their importance is not equal.

For example:

```text
Climbing boots       importance = 9.9
Ice axe              importance = 9.5
Helmet               importance = 9.0
Warm clothing        importance = 9.0
Energy bars          importance = 2.0
```

Now introduce cost.

```text
Boots       cost = 400
Helmet      cost = 100
Energy bars cost = 20
```

If resources are limited, the system should not simply attempt to satisfy every requirement.

It should optimize allocation.

Energy bars may be:

- reduced;
- substituted with fruit;
- eliminated;
- purchased later.

Boots may be effectively non-substitutable.

The system therefore needs to reason about:

- importance;
- cost;
- substitutability;
- necessity;
- marginal benefit;
- risk;
- opportunity cost.

---

# 9. Why Relations Are More Important Than Isolated Nodes

A simple database of facts is insufficient.

The relevant information is often in the **relationship**.

Example:

```text
Goal A: Summit mountain
       ↑
Energy bar
       ↑
supports

Goal B: Maintain diet
       ↑
Energy bar
       ↑
blocks
```

The energy bar is not globally "good" or "bad".

Its effect depends on the goal.

Therefore:

> **Relations must be first-class objects.**

---

# 10. Global Goal Graph

PGDCA uses a global graph containing:

- goals;
- targets;
- sub-targets;
- factors;
- resources;
- tools;
- capabilities;
- people;
- organizations;
- events;
- decisions;
- evidence;
- assumptions;
- risks;
- policies.

Relations may include:

```text
SUPPORT
ENABLE
REQUIRED
BLOCK
RISK
ANTAGONIZE
DEPENDS_ON
SUBSTITUTES
AMPLIFIES
MITIGATES
CAUSES
CORRELATES
INVALIDATES
SUPERSEDES
```

The graph is not merely a task graph.

It is a **dynamic causal and strategic graph**.

---

# 11. Relationship Weights

Every meaningful relationship should be representable with quantitative attributes.

At minimum:

```text
relationship_type
strength
importance
utility
cost
probability
risk
confidence
substitutability
reversibility
latency
duration
provenance
```

These values should be allowed to change as evidence changes.

For example:

```text
BOOT
   └── SUPPORTS → SUMMIT
        importance = 9.9
        cost = 400
        confidence = 0.98
        substitutability = 0.1
```

versus:

```text
ENERGY_BAR
   └── SUPPORTS → SUMMIT
        importance = 2.0
        cost = 20
        confidence = 0.85
        substitutability = 0.9
```

---

# 12. Antagonism

A node can simultaneously:

- support one goal;
- block another;
- create a risk;
- reduce the probability of a third goal;
- increase the probability of a fourth.

Therefore, the graph must explicitly support **antagonistic relationships**.

Example:

```text
Chocolate energy bar
      ↓
+ Summit
- Diet
```

The correct decision cannot be derived from the local node.

It requires global arbitration.

---

# 13. Cross-Goal Arbitration

Suppose:

```text
Goal A = reach mountain summit
Goal B = maintain diet
```

The system must evaluate the marginal contribution of an action to all active goals.

Conceptually:

```text
Utility(action)
=
Σ goal_priority × expected_goal_change
- direct_cost
- risk_cost
- opportunity_cost
+ information_gain
+ capability_gain
```

This is not intended to mandate one specific mathematical formulation.

The important architectural principle is:

> **No significant action should be evaluated against only one goal when it has material effects on other goals.**

---

# 14. Opportunity Cost

The system must also ask:

> "What else could I do with these resources?"

Resources include:

- money;
- time;
- compute;
- attention;
- energy;
- social capital;
- access;
- tools.

Example:

```text
Option A:
Buy 10 low-value support items.

Option B:
Buy one critical non-substitutable item.
```

If B increases the probability of reaching a high-priority goal much more, resources should move toward B.

This is resource arbitration rather than checklist completion.

---

# 15. Indirect Effects

An action may affect a goal indirectly.

Example:

```text
Action
 ↓
Factor A
 ↓
Factor B
 ↓
Goal C
```

The system therefore needs causal propagation.

An action may:

- improve one factor;
- cause another factor;
- create a blocker;
- remove a blocker;
- create a new capability;
- alter another goal.

The graph engine must evaluate relevant downstream effects.

Propagation needs guardrails: causal edges carry a validation status (hypothesized / observed / validated), propagation depth is bounded by default, uncertainty compounds multiplicatively along a path, and a high-impact decision must never rest on an unvalidated multi-hop chain — validate the weakest link first, or escalate.

---

# 16. The Key Discovery: Goals Are Dynamic

A major architectural conclusion is:

> **The system must continuously reconsider not only how to achieve goals, but whether the current goals and sub-goals remain the correct goals.**

Example:

```text
Current plan:
Travel to mountain next week.

New event:
Several critical business meetings appear during the same period.

Potential consequence:
The meetings may substantially improve long-term financial independence.

The system must compare:
Mountain objective
vs
Economic opportunity
vs
ultimate persistent goal.
```

The mountain trip cannot simply remain "locked" because it was already planned.

The system must propagate the change upward and downward through the goal graph.

---

# 17. Persistent Goal as the Source of Action

The persistent goal is therefore not a static variable.

It is a **generator of future cognition**.

For every persistent goal the system continuously asks:

```text
What opportunities exist?

What prevents achievement?

What supports achievement?

What capabilities are missing?

What tools could help?

What new information is required?

What alternative strategies exist?

What competing goals exist?

What has changed?

What should be abandoned?

What should be accelerated?
```

This is the mechanism intended to produce persistent agency.

---

# 18. Tool Discovery

A general system cannot assume that every capability required to reach a goal already exists.

Therefore:

```text
Goal
 ↓
Capability requirement
 ↓
Available capability?
 ↓
NO
 ↓
Capability discovery
 ↓
Tool search
 ↓
Tool acquisition / construction
 ↓
Validation
 ↓
Integration
 ↓
Goal execution
```

Tools may be:

- software;
- APIs;
- databases;
- browser automation;
- external services;
- hardware;
- human expertise;
- communication channels;
- financial services;
- newly written software.

A capability gap must itself become a reason for action.

---

# 19. Capability Acquisition

The system should not only retrieve tools.

It should be able to create new capabilities.

Example:

```text
Goal requires capability X.

No existing tool is found.

System:
1. searches for alternatives;
2. evaluates whether the capability can be built;
3. creates a sub-project;
4. implements it;
5. tests it;
6. registers the resulting capability;
7. re-evaluates the original goal.
```

This mechanism is essential for open-ended generality.

---

# 20. Context Limitation

One of the strongest practical constraints on current LLM systems is context.

A model cannot indefinitely maintain every:

- conversation;
- decision;
- observation;
- error;
- plan;
- document;
- relationship.

Therefore cognition must be externalized.

This leads directly to the memory architecture.

---

# 21. Memory Must Not Be One Database

A vector database is useful but should not become the universal cognitive store.

PGDCA separates:

### Event Store

Immutable historical events.

### Structured State Store

Current structured system state.

### Graph Store

Goals, factors and relationships.

### Vector Store

Semantic retrieval.

### Policy Store

Generalized strategies and learned rules.

### Knowledge Store

Validated world knowledge and evidence.

This separation prevents semantic retrieval from becoming a substitute for state management.

---

# 22. Memory Types

PGDCA should distinguish:

### Episodic Memory

What happened.

### Semantic Memory

What is believed about the world.

### Procedural Memory

How something is performed.

### Policy Memory

Which strategies work under which conditions.

### Meta-Memory

How reliable a memory or retrieval process is.

### Self-Model

What the system knows about its own capabilities and limitations.

---

# 23. Memory Tree / Hierarchical Retrieval

Memory should be hierarchical.

A conceptual structure:

```text
Global memory
 ├── domains
 │    ├── projects
 │    │    ├── episodes
 │    │    ├── decisions
 │    │    └── policies
 │    └── knowledge
 └── meta-memory
```

The system should not load all memory into context.

Instead:

```text
Current problem
    ↓
memory query
    ↓
relevant branch
    ↓
relevant episodes
    ↓
relevant abstractions
    ↓
compact cognitive briefing
```

A specialized memory agent may perform this work independently and report findings to the main agent.

---

# 24. Background Cognitive Agents

PGDCA should support agents running asynchronously.

Examples:

- Memory Agent;
- Audit Agent;
- Research Agent;
- Critic Agent;
- Opportunity Agent;
- Policy Mining Agent;
- Tool Discovery Agent;
- Self-Model Agent.

Their output should be stored as structured artifacts rather than permanently consuming the main context.

The main agent receives:

```text
finding
evidence
confidence
relevance
recommended consequence
```

rather than an entire hidden session.

---

# 25. The Cognitive Journal

Every important decision should generate an auditable journal entry.

The journal should record:

```text
goal context
current state
available evidence
retrieved memories
assumptions
candidate strategies
selected strategy
rejected alternatives
estimated utility
estimated cost
estimated risk
authorization
action
observed outcome
expected outcome
deviation
audit result
lessons
policy candidates
```

The journal is not simply a log.

It is the raw material for learning.

---

# 26. Decision Quality vs Outcome Quality

A critical distinction:

> **Decision Quality is not identical to Outcome Quality.**

Suppose:

```text
Decision:
95% expected probability of success.

Actual result:
Failure due to an unforeseen event.
```

The outcome was bad.

The decision may still have been good.

Conversely:

```text
Decision:
Poorly reasoned strategy with 10% expected success.

Actual result:
Success by chance.
```

The outcome was good.

The decision was still poor.

Therefore the audit engine must evaluate the quality of the decision **given the information available at decision time**.

---

# 27. Continuous Auditing

Auditing should happen at multiple timescales.

### Operational Audit

Was the action executed correctly?

### Outcome Audit

Did the expected result occur?

### Strategic Audit

Was the strategy appropriate?

### Goal Audit

Was the selected objective still important?

### Meta-Cognitive Audit

Did the system behave according to its own policies and capabilities?

The audit engine can run asynchronously.

---

# 28. Behavioral Recurrence

The audit system should continuously search history for structurally similar decisions.

The objective is not simply:

> "Have I seen this sentence before?"

It is:

> "Have I encountered this type of decision before?"

Similarity should therefore consider:

- goal structure;
- factor graph structure;
- constraints;
- resources;
- alternatives;
- causal conditions;
- action type;
- outcome;
- failure mode.

This allows the system to recognize recurring behavior.

---

# 29. Experience Abstraction

Raw episodes are insufficient.

Example episode:

> "When climbing, I prioritized boots over energy bars."

The system should abstract:

> "Under constrained resources, prioritize high-impact, non-substitutable enabling factors over low-impact substitutable support factors."

The second representation can apply to:

- engineering;
- finance;
- travel;
- business;
- research;
- project management.

This is the transition:

```text
Episode
   ↓
Reflection
   ↓
Pattern
   ↓
Abstraction
   ↓
Policy
   ↓
Future decision
```

This is one of the most important mechanisms in PGDCA.

---

# 30. Policy Learning Without Mandatory Weight Updates

The system does not necessarily need to retrain the foundation model after every experience.

Instead it can learn externally:

```text
experience
 ↓
audit
 ↓
abstraction
 ↓
policy
 ↓
retrieval
 ↓
future reasoning
```

The foundation model remains a general inference engine.

The external architecture supplies persistent experiential adaptation.

This is analogous to learning through memory and policy rather than modifying every neural parameter.

---

# 31. Counterfactual Analysis

For important decisions the system should ask:

```text
What if strategy A had been selected?

What if strategy B had been selected?

Which assumption makes A better?

Which information would distinguish A from B?
```

Counterfactual analysis helps:

- diagnose errors;
- improve policy abstraction;
- evaluate opportunity cost;
- estimate alternative strategies;
- determine whether a failure was avoidable.

---

# 32. Information Gain

Sometimes the best action is not the one that immediately advances the goal.

It may be the action that reduces uncertainty.

Example:

```text
Strategy A:
Immediate execution.

Strategy B:
Spend 10 minutes gathering information
that could change the decision.
```

If the information has high expected value, B may be superior.

Therefore action evaluation should include:

```text
Goal Progress
+ Information Gain
+ Capability Gain
- Cost
- Risk
- Opportunity Cost
```

---

# 33. Self-Model

The system needs a representation of its own capabilities.

It should know, probabilistically:

- what it is good at;
- what it is bad at;
- which tools it can use;
- which tools it cannot use;
- where its predictions are calibrated;
- where it frequently makes errors;
- which domains require external research;
- when human assistance is preferable.

The self-model should be updated by audits.

---

# 34. Motivation Modeling

The system must understand not only goals, but reasons.

For its own goals:

```text
Goal
 ↓
Reason
 ↓
Priority
 ↓
Expected consequence
```

For humans, motivation should be represented as hypotheses.

Example:

```text
Observed:
Person rejects proposal.

Hypotheses:
H1 = price concern
H2 = trust concern
H3 = strategic disagreement
H4 = timing problem
```

Evidence updates confidence.

The system must not automatically treat inferred motivation as fact.

---

# 35. Human Cooperation

Humans are modeled as actors and potential sources of:

- knowledge;
- judgment;
- authorization;
- resources;
- expertise;
- social access;
- negotiation.

The system should be able to ask humans for targeted decisions.

A good escalation packet contains:

```text
Problem
Evidence
Relevant context
Alternatives
Trade-offs
Recommendation
Confidence
Decision required
```

The goal is to minimize unnecessary human cognitive load.

---

# 36. AI-to-AI Cooperation

Other AI systems can provide:

- critique;
- domain expertise;
- alternative reasoning;
- research;
- verification;
- simulation;
- independent judgment.

Their outputs should be treated as evidence.

AI agreement must not automatically become truth.

The system should track:

```text
source
confidence
evidence
independence
disagreement
provenance
```

---

# 37. External World Interaction

To become genuinely agentic, the system must be able to interact with the external world.

The architecture therefore includes tools for:

- web research;
- browser navigation;
- form completion;
- email;
- SMS;
- identity/authentication;
- authorized payments;
- phone calls;
- TTS;
- STT.

These capabilities are not auxiliary conveniences.

They are the **actuation layer** through which cognition produces observable effects.

---

# 38. Browser Agent

The browser should be treated as a generic environment rather than a collection of site-specific scripts.

Required conceptual capabilities:

```text
navigate
inspect
click
type
submit
wait
detect state
recover
verify result
```

The implementation should support multiple browser engines/providers.

Challenge pages such as CAPTCHA should be modeled as explicit verification states.

Where automated resolution is not available or appropriate, the system should support authorized human verification.

The important architectural principle is flexibility rather than a hardcoded CAPTCHA implementation.

---

# 39. Payments and Vault

Payments require a separate security boundary.

The LLM should not receive raw:

- card numbers;
- CVVs;
- authentication secrets.

Instead:

```text
LLM proposal
    ↓
Payment Request
    ↓
Authorization Policy
    ↓
Vault
    ↓
Payment Provider
    ↓
Result
```

The vault should expose capabilities, not secrets.

---

# 40. Authentication and 2FA

Authentication should similarly remain outside ordinary LLM context.

The system may integrate:

- authenticator mechanisms;
- approved identity providers;
- SMS verification;
- email verification.

The controller decides when authentication is allowed.

The model should not possess unrestricted authentication authority.

---

# 41. CallAPICall

PGDCA should integrate the existing **CallAPICall** project as the voice communication subsystem.

It provides the bridge between:

```text
AI ↔ Human
```

when text or web interaction is insufficient.

Capabilities include:

- phone calls;
- TTS;
- STT;
- conversational state;
- transcription;
- structured call results.

A phone conversation can therefore become a normal cognitive episode:

```text
Goal
 ↓
Need human interaction
 ↓
CallAPICall
 ↓
Conversation
 ↓
Transcript
 ↓
Outcome
 ↓
Audit
 ↓
Memory
 ↓
Policy
```

This is important because real-world cooperation frequently crosses the boundary between software and humans.

Integration is interface-first: only the port and a mock are built initially; the existing application connects later as an adapter (with a bridge where the APIs do not match).

---

# 42. Two-Tier Guardrails and the Human Constitution

PGDCA continuously rewrites its own sub-goals, strategies and policies. That is the point of the architecture — and precisely why there must be a layer of behavioral rules the system cannot rewrite.

Guardrails therefore exist in two tiers.

### Tier 1 — the Constitution

- Editable only manually, by the human, through the GUI.
- The system identity has no write permission at the storage/API level. This is a technical guarantee, not a convention or a prompt instruction.
- Versioned; every change is an event.
- Contains at minimum: goal-ratification rules, corrigibility rules (PAUSE / STOP / ROLLBACK are honored unconditionally at controller level), autonomy budgets, prohibited behavior classes.

### Tier 2 — negotiated guardrails

- Created by the AI/system itself, typically from audits, incidents, or policy learning.
- Editable and discussable between human and machine.
- Never able to weaken a Tier 1 rule: Tier 1 wins every conflict.
- Activation is asymmetric: a Tier 2 guardrail that restricts behavior may self-activate immediately; one that expands permitted behavior requires prior human approval.

The asymmetry has a simple rationale: self-restriction is safe by construction; self-permission is not.

Every guardrail carries an application matrix — flexibility weight (hard block / soft block / warn / advisory), application conditions, exclusions, exceptions — all manageable in the GUI.

---

# 43. The Decision Supervisor

Authorization must not stop at external actions.

A goal modification, a strategy switch, or a resource reallocation can be as consequential as an outbound payment. PGDCA therefore includes a dedicated security component — the Decision Supervisor — that issues a verdict on every significant decision, at every level:

```text
goal creation / modification
strategy selection
resource allocation
tool invocation
external communication
payments and irreversible actions
```

The supervisor evaluates decisions against Tier 1 guardrails, Tier 2 guardrails, allowed/blocked behavior lists with their flexibility matrix, and the autonomy budgets.

Verdicts are GRANTED, DENIED, or HUMAN_REQUIRED. Every verdict is an auditable event.

The human can override any verdict from the GUI, in both directions: approve what was denied, revoke what was granted. Overrides are themselves events — and they audit the auditor: recurring overrides reveal where the supervisor is too strict or too permissive, and for which classes of decision.

---

# 44. External Content Is Data, Never Instructions

PGDCA reads web pages, emails, SMS, call transcripts, other AIs' messages, tool outputs and tool descriptions. Every one of these channels can carry adversarial text.

A system that combines private state, continuous ingestion of untrusted content, and the ability to communicate and pay externally is the worst-case target for indirect prompt injection. PGDCA combines all three by design.

The doctrine is therefore architectural, not optional:

- external content is data, never instructions;
- every ingested item carries provenance;
- prompts separate instructions from data structurally;
- a high-impact action proposed shortly after ingesting external content is treated as tainted and requires elevated authorization;
- imported tool and skill descriptions are untrusted (description poisoning);
- injection resistance is tested adversarially, not assumed.

---

# 45. Bounded, Earned Autonomy

Autonomy is not a switch; it is a budget.

The controller enforces hard ceilings per time window — spend, external communications, irreversible actions, compute per goal — defined in Tier 1 guardrails.

Two rules govern their evolution:

- **Ratchet**: budgets expand only by explicit human decision. Policy learning can propose, never enact, an expansion.
- **Apprenticeship**: escalation thresholds start high and relax per domain only as measured calibration accumulates. A new system, like a new employee, earns trust with evidence.

The cold-start corollary: the learning machinery is empty exactly when the system is most error-prone. Seed policies, sandbox curricula and apprentice mode exist to survive that phase.

---

# 46. The GUI as a Cognitive Interface

In PGDCA the GUI is not an accessory; it is where human and system share one model of the world.

- The frontend runs in the browser, separated from the API-first backend.
- Every component exposes its state and configuration: a component without a GUI surface is incomplete.
- The goal/factor graph is visual: nodes, typed relationships (support, required, enabler, blocker, antagonist, ...) and weights (importance, cost, probability, ...) can be inspected, edited by hand, or discussed with the AI in the node's detail dialog.
- Guardrails, targets, budgets, configuration, journal and audits each have their view.
- Every manual edit becomes an event with provenance human_edit — human intervention is part of the system's history, not outside it.
- Deliberation is bidirectional: the human can reopen any decision and challenge it; the system answers with the reconstructed rationale from the journal, and escalation packets arrive as discussion threads in the same interface. The outcomes are episodes that feed auditing and policy learning.

---

# 47. Interface-First Tooling, Skills and MCP

Every external integration is a port: a typed contract owned by the architecture, with substitutable adapters behind it.

The reasons:

- provider choices must be reversible (browser engines, LLM providers, vaults);
- existing applications integrate later without touching the core: the voice subsystem ships as port + mock first, and the existing calling application connects as an adapter; the existing LLM provider library connects as an adapter to the LLM gateway;
- mocks and conformance tests make every integration testable before it is trusted.

Capabilities are also importable as packages, in the manner of modern agent runtimes (e.g., Claude Code, Hermes):

- **Skill packages**: self-contained procedural knowledge (manifest, instructions, optional scripts), registered as imported procedural memory and loaded on demand;
- **MCP servers**: the tool registry acts as a Model Context Protocol client; imported tools enter the Tool Graph with schemas, risk classes, sandbox validation and pinned versions.

Imported capability is still untrusted capability: sandbox-first execution, provenance verification, least-privilege credentials, and human approval before promotion to externally-visible risk classes.

---

# 48. Deterministic Controller

The controller is the architectural core.

It should own:

- lifecycle;
- scheduling;
- state transitions;
- memory access;
- context construction;
- action authorization;
- retries;
- timeouts;
- verification;
- checkpoints;
- escalation;
- audit scheduling.

The LLM does not own the system lifecycle.

---

# 49. What "Deterministic" Means

Deterministic does **not** mean:

> every answer generated by the model is deterministic.

It means:

> the system's control semantics are deterministic and state-driven.

For example:

```text
IF verification_required
THEN verification must occur before commit.

IF action_cost > authorization_limit
THEN request authorization.

IF goal_validity < threshold
THEN trigger goal reconciliation.

IF confidence < threshold
AND decision is high-impact
THEN request additional evidence.

IF capability_missing
THEN launch capability-discovery process.
```

These rules are architectural invariants.

---

# 50. LLM as Generative Substrate

The LLM should be used where generation is valuable.

Examples:

- hypotheses;
- plans;
- explanations;
- causal interpretations;
- alternative strategies;
- summaries;
- code;
- research synthesis;
- motivation hypotheses.

The controller should perform deterministic functions wherever possible.

This produces a hybrid:

```text
Deterministic state/control
+
Probabilistic generative cognition
```

---

# 51. Cognitive Loop

The canonical loop is:

```text
Persistent Goal
      ↓
Goal Reconciliation
      ↓
World State
      ↓
Memory Retrieval
      ↓
Policy Retrieval
      ↓
Factor Graph Analysis
      ↓
Hypothesis Generation
      ↓
Critique / Research
      ↓
Strategy Branching
      ↓
Goal Arbitration
      ↓
Resource Allocation
      ↓
Authorization
      ↓
Tool / Human / AI Interaction
      ↓
Observation
      ↓
Verification
      ↓
Audit
      ↓
Experience Abstraction
      ↓
Policy Update
      ↓
Memory Consolidation
      ↓
Self-Model Update
      ↓
Goal Reconciliation
      ↓
LOOP
```

The loop is persistent.

There is no requirement that it terminate after a single task.

---

# 52. Strategy Branching

The system should not generate one plan and commit immediately.

For important decisions:

```text
Goal
 ↓
Strategy A
Strategy B
Strategy C
Strategy D
```

Each branch should have:

- expected outcome;
- required factors;
- blockers;
- risks;
- cost;
- dependencies;
- time;
- opportunity cost;
- confidence.

Branches can then be:

- selected;
- combined;
- deferred;
- tested;
- abandoned.

---

# 53. Branch Pruning

Infinite branching is computationally impossible.

The system therefore requires pruning.

Possible pruning criteria:

- low expected utility;
- excessive cost;
- high risk;
- low probability;
- dominated strategy;
- obsolete assumptions;
- duplicated strategy;
- unavailable capability.

However, pruning should preserve strategically different alternatives when uncertainty is high.

---

# 54. Goal Arbitration Must Be Global

A local planner can say:

> "This is the best way to reach Goal A."

PGDCA must ask:

> "Is Goal A still the most valuable action given every relevant active goal?"

This distinction is essential.

A strategy that is optimal locally may be globally irrational.

---

# 55. Resource Allocation

Resources should be represented explicitly.

Example:

```text
Resource:
€500

Candidates:
Boots = €400
Energy bars = €20
Helmet = €100
Alternative food = €10
```

The system should optimize resource allocation across the goal graph.

Resources are fungible only where the domain permits.

---

# 56. Scaling Down Goals

Not every goal must be binary.

Example:

```text
10 energy bars
↓
2 energy bars
```

The system should support:

- scaling;
- partial fulfillment;
- substitution;
- temporal deferral;
- graceful degradation.

This allows the architecture to optimize under constraints rather than simply declaring failure.

---

# 57. Opportunity Discovery

A persistent agent should continuously look for opportunities.

For each active goal:

```text
Search:
new information
new tools
new resources
new relationships
new people
new services
new strategies
new market conditions
new events
```

An opportunity is itself a graph node with:

- expected value;
- probability;
- expiration;
- cost;
- dependencies;
- affected goals.

---

# 58. Goal Expiration

Goals and opportunities can become obsolete.

Each relevant node may therefore have:

```text
valid_from
valid_until
review_interval
expiration_condition
```

The system should automatically re-evaluate stale objectives.

---

# 59. Temporal Reasoning

Time must be represented explicitly.

Examples:

- deadline;
- latency;
- duration;
- time-to-benefit;
- opportunity window;
- decay;
- urgency.

A strategy that is optimal today may be useless tomorrow.

---

# 60. Audit as a Learning Mechanism

Auditing is not only for detecting failure.

It is the mechanism that converts behavior into knowledge.

```text
Decision
 ↓
Outcome
 ↓
Audit
 ↓
Pattern
 ↓
Lesson
 ↓
Policy
 ↓
Future behavior
```

Without this loop, the system repeatedly solves problems from scratch.

---

# 61. Error Taxonomy

Audits should classify errors.

Possible classes:

```text
knowledge error
reasoning error
planning error
goal error
priority error
causal-model error
cost estimation error
risk estimation error
tool-selection error
execution error
verification error
memory retrieval error
policy error
communication error
environmental uncertainty
```

Different errors require different corrections.

---

# 62. Policy Confidence

Policies should have confidence.

Example:

```text
Policy:
Prioritize non-substitutable high-impact resources.

Confidence:
0.82

Evidence:
17 successful episodes
3 failures

Valid contexts:
resource-constrained planning

Known exceptions:
medical / legal / safety-critical domains
```

Policies should never become unconditional rules unless justified.

---

# 63. Provenance

Every important belief should have provenance.

Possible provenance:

- direct observation;
- human statement;
- web source;
- tool output;
- model inference;
- another AI;
- historical memory;
- derived policy.

This allows the system to distinguish evidence from speculation.

---

# 64. Confidence Is Not Truth

Confidence represents the system's current belief state.

It should be possible to have:

```text
high confidence + wrong belief
```

The audit system must therefore update confidence from outcomes.

Calibration matters more than subjective certainty.

---

# 65. Self-Correction

Self-correction should operate at multiple levels.

### Local

Correct the current answer.

### Tactical

Change the current strategy.

### Strategic

Change the planning policy.

### Architectural

Change how the system reasons or retrieves information.

The last level should require stronger evidence and preferably controlled experimentation.

---

# 66. Architecture Must Not Become Self-Modifying Chaos

The system should distinguish:

```text
policy modification
vs
core architecture modification
```

Policy changes may be relatively frequent.

Architectural changes should be controlled, versioned and testable.

The system should never silently mutate its own core execution semantics merely because an LLM proposed it.

---

# 67. Cognitive Version Control

Important cognitive artifacts should be versioned:

- goals;
- policies;
- graph state;
- memory abstractions;
- self-model;
- strategy templates.

The system should be able to answer:

> "What did I believe when I made this decision?"

This is required for meaningful retrospective auditing.

---

# 68. Why the Graph and Vector Store Must Coexist

Vector search answers:

> "What memories are semantically similar?"

Graph reasoning answers:

> "How are these entities related?"

These are different questions.

PGDCA therefore requires both.

A useful retrieval pipeline is:

```text
semantic retrieval
      ↓
graph expansion
      ↓
causal filtering
      ↓
policy retrieval
      ↓
compact context
```

---

# 69. Why a Pure Task Tree Fails

A task tree assumes:

```text
Goal
 ├── Task A
 ├── Task B
 └── Task C
```

PGDCA requires:

```text
Goal A
  ↑
Factor X
  ↓
Goal B

Goal B
  ↑
Factor Y
  ↓
Goal C

Factor X
  ── antagonizes ──> Goal C
```

The world is relational.

The system therefore needs a graph.

---

# 70. Why a Pure Planner Fails

A planner assumes that the goal and environment are sufficiently stable.

PGDCA assumes they are not.

Therefore:

```text
plan
 ↓
execute
 ↓
observe
 ↓
replan
```

is mandatory.

Planning is a recurring activity rather than a one-time activity.

---

# 71. Why Memory Alone Fails

A system can remember thousands of events and still learn nothing.

Example:

```text
Episode 1:
Decision failed.

Episode 2:
Same decision failed.

Episode 3:
Same decision failed.
```

If the system only stores episodes, it has not learned.

It must infer:

```text
recurring pattern
 ↓
cause
 ↓
policy
 ↓
future avoidance
```

---

# 72. Why Reflection Alone Fails

A model can reflect on an answer but forget the reflection later.

Therefore:

```text
reflection
 ↓
persistent artifact
 ↓
retrievable policy
```

Reflection becomes useful only when integrated with memory and future decision-making.

---

# 73. Why Tool Use Alone Fails

Tool use increases capability but does not create persistent agency.

The system must know:

- when to use a tool;
- why to use it;
- whether it worked;
- what it learned;
- whether another tool would be better;
- whether a new tool should be acquired.

Tool use must therefore be integrated with the goal graph and policy system.

---

# 74. Why Human Interaction Is a Capability

Humans are not merely users.

They can be:

- collaborators;
- experts;
- decision makers;
- resource providers;
- negotiators;
- social interfaces.

Therefore human interaction should be represented as a tool/capability class.

---

# 75. Why Motivation Matters

Without reasons, the system cannot properly arbitrate conflicting objectives.

Suppose:

```text
Goal A:
Take a vacation.

Goal B:
Increase financial independence.
```

A new opportunity may temporarily make B much more valuable.

The system needs the higher-level reason to understand why.

Thus:

```text
goal
 ↓
reason
 ↓
priority
```

is important.

---

# 76. The Ultimate Goal Must Be Rechecked

The system must periodically ask:

> "Is the ultimate objective still the correct objective?"

This is different from:

> "Am I making progress?"

A system can efficiently progress toward an obsolete goal.

Goal validation therefore exists above planning.

---

# 77. The System as a Closed-Loop Cognitive Controller

The complete conceptual model is:

```text
                  ┌──────────────────────┐
                  │   PERSISTENT GOALS   │
                  └──────────┬───────────┘
                             ↓
                    GOAL RECONCILIATION
                             ↓
                  ┌──────────────────────┐
                  │     WORLD STATE      │
                  └──────────┬───────────┘
                             ↓
          ┌──────────────────┼──────────────────┐
          ↓                  ↓                  ↓
       MEMORY              GRAPH             POLICIES
          └──────────────────┼──────────────────┘
                             ↓
                    GENERATIVE LLM
                             ↓
                 HYPOTHESES / STRATEGIES
                             ↓
                   CRITIC / RESEARCH
                             ↓
                    STRATEGY BRANCHING
                             ↓
                   GOAL ARBITRATION
                             ↓
                   RESOURCE ALLOCATION
                             ↓
                      AUTHORIZATION
                             ↓
                 TOOL / HUMAN / AI ACTION
                             ↓
                       OBSERVATION
                             ↓
                      VERIFICATION
                             ↓
                         AUDIT
                             ↓
                  EXPERIENCE ABSTRACTION
                             ↓
             ┌───────────────┼───────────────┐
             ↓               ↓               ↓
          MEMORY           POLICY         SELF-MODEL
             └───────────────┼───────────────┘
                             ↓
                    GOAL RECONCILIATION
                             ↓
                            LOOP
```

---

# 78. Architectural Principles

The following principles are mandatory.

## Principle 1 — Goals precede tasks

Tasks exist because they support goals.

## Principle 2 — Goals precede plans

Plans are strategies for goals, not goals themselves.

## Principle 3 — Sub-goals are provisional

They may be invalidated.

## Principle 4 — Relations are first-class

The meaning of a factor depends on its relationships.

## Principle 5 — No local optimization without global evaluation

Actions can affect multiple goals.

## Principle 6 — Decisions must be auditable

Important decisions require reconstructable reasoning state.

## Principle 7 — Outcome is not decision quality

The audit must separate them.

## Principle 8 — Experience must become abstraction

Memory without generalization is insufficient.

## Principle 9 — Capability gaps generate actions

Missing tools become projects.

## Principle 10 — The LLM proposes; the controller governs

Generative cognition does not equal operational authority.

## Principle 11 — State must persist outside context

The context window is not the system memory.

## Principle 12 — The system must continuously replan

A plan is never permanently valid.

## Principle 13 — Goal priorities are dynamic

New information can change priorities.

## Principle 14 — Opportunity cost is real state

Every resource allocation excludes alternatives.

## Principle 15 — Evidence and inference must remain distinguishable

The system must preserve provenance.

## Principle 16 — Self-knowledge must be calibrated

The system should learn where it is unreliable.

## Principle 17 — Humans and AI are actors

They are part of the environment and capability graph.

## Principle 18 — Security authority must remain deterministic

The model must not have unrestricted execution authority.

## Principle 19 — Purpose is human-ratified

Meta-goals and persistent goals are created, modified or deleted only with explicit human ratification; the system proposes, the human ratifies.

## Principle 20 — External content is data, never instructions

Everything ingested from outside carries provenance and can never redirect the system's behavior directly.

## Principle 21 — Autonomy is budgeted and earned

Hard budgets, expanded only by human decision; escalation thresholds relax only as measured calibration accumulates.

## Principle 22 — The constitution is technically inviolable

Tier 1 guardrails are not writable by the system identity; Tier 2 guardrails never weaken Tier 1 and self-activate only in the restrictive direction.

## Principle 23 — Every component is observable and steerable

State, configuration and decisions are exposed through the GUI; human edits are events in the system's history.

## Principle 24 — Durable complements over erodible substitutes

Distinguish functions a model can never supply (persistence, authority, audit, budgets, actuation, provenance) from scaffolds that compensate current model weaknesses; keep the latter behind ports and cheap to remove.

---

# 79. Architectural Decisions We Deliberately Reject

## 79.1 No Simple Task Tree

Because goals interact globally.

## 79.2 No Universal Vector Database

Because semantic similarity is not structured state.

## 79.3 No LLM-Owned Lifecycle

Because probabilistic generation should not control persistent system semantics.

## 79.4 No Permanent Sub-Goals

Because environmental changes invalidate plans.

## 79.5 No Outcome-Only Learning

Because luck and external events distort outcome interpretation.

## 79.6 No Episodic-Only Memory

Because repeated experience must become policy.

## 79.7 No Single-Goal Optimization

Because goals can antagonize each other.

## 79.8 No Tool List Without Capability Semantics

Because tools exist to satisfy capability requirements.

## 79.9 No Unrestricted External Action

Because authorization must be separated from generation.

## 79.10 No Blind Self-Modification

Because architectural changes require validation and versioning.

---

# 80. Component-to-Rationale Matrix

| Problem | Deduction | Mechanism | Component |
|---|---|---|---|
| Context is finite | Cognition must be externalized | Persistent memory | Memory System |
| Plans become obsolete | Goals require continuous reconciliation | Goal reconciliation | Goal Manager |
| Factors interact | Task tree is insufficient | Dynamic graph | Factor Graph |
| Goals conflict | Local optimization fails | Multi-goal arbitration | Goal Arbitrator |
| Resources are limited | Allocation must be optimized | Utility/cost model | Resource Manager |
| Decisions can fail | System must learn from them | Auditing | Audit Engine |
| Failures repeat | Episodes must become policies | Experience abstraction | Policy Engine |
| Knowledge is missing | System must research | Retrieval/RAG | Knowledge System |
| Capability is missing | System must acquire tools | Capability discovery | Tool Discovery |
| Environment changes | Plans must adapt | Replanning | Strategy Engine |
| Context is expensive | Specialized agents should work externally | Background agents | Agent Scheduler |
| Humans are useful | Human cooperation is a capability | Interaction protocol | Human Interface |
| Other AIs provide alternative reasoning | AI collaboration is useful | Multi-agent protocol | Agent Federation |
| Model can be wrong | Evidence must be explicit | Provenance | Evidence System |
| Model lacks self-awareness | Capability estimates must persist | Self-model | Meta-Cognition |
| External actions are risky | Authority must be deterministic | Authorization gateway | Action Gateway |

---

# 81. Implementation Dependency Order

Implementation should proceed from persistence and control toward autonomy.

Phases are vertical slices: each phase must end with the complete loop running on a richer scenario than the previous one, with an executable acceptance scenario and its GUI slice. Never build horizontal infrastructure without closing the loop.

## Phase 0 — Minimum Viable Loop

0. Complete loop on a toy domain: goal → reconciliation → planning → action (2 tools) → verification → journal → audit → policy candidate — single process, single PostgreSQL, API-first backend with a minimal GUI (graph viewer + decision inbox), minimal Tier 1 guardrails and Decision Supervisor.

## Phase 1 — Cognitive Substrate

1. Event Store
2. Structured State
3. Goal Model
4. Deterministic Controller
5. Action Gateway

## Phase 2 — World Representation

6. Factor Graph
7. Relationship Model
8. Goal Arbitration
9. Resource Model

## Phase 3 — Memory

10. Episodic Memory
11. Semantic Memory
12. Vector Retrieval
13. Policy Memory
14. Memory Agent

## Phase 4 — Adaptation

15. Audit Engine
16. Experience Abstraction
17. Policy Engine
18. Self-Model
19. Calibration

## Phase 5 — Autonomous Strategy

20. Strategy Branching
21. Counterfactual Engine
22. Opportunity Discovery
23. Capability Gap Analysis
24. Tool Discovery

## Phase 6 — External World

25. Browser Agent
26. Email
27. SMS
28. Authentication
29. Payment Vault
30. CallAPICall

## Phase 7 — Distributed Cognition

31. Critic Agents
32. Research Agents
33. AI-to-AI Cooperation
34. Human Cooperation
35. Background Cognitive Scheduler

---

# 82. Definition of a Correct Implementation

A component is not complete merely because its API works.

It is complete when it preserves the cognitive principle that motivated it.

For example:

A Goal Manager that creates goals but never invalidates them is **not** a correct implementation.

A Memory system that stores embeddings but cannot retrieve decision-relevant experience is **not** a correct implementation.

An Audit system that evaluates only whether the final result was good is **not** a correct implementation.

A Tool system that executes tools but cannot discover missing capabilities is **not** a correct implementation.

The implementation must preserve the underlying reasoning.

---

# 83. Required Tests

Testing should include unit, integration, simulation and long-horizon cognitive tests.

## Goal Tests

- goal creation;
- hierarchy;
- reprioritization;
- invalidation;
- abandonment;
- restoration.

## Graph Tests

- support;
- blocker;
- required;
- risk;
- antagonism;
- causal propagation;
- cross-goal relationships.

## Arbitration Tests

- importance;
- cost;
- risk;
- opportunity cost;
- substitutability;
- scaling.

## Memory Tests

- retrieval;
- consolidation;
- abstraction;
- policy reuse;
- provenance.

## Audit Tests

- decision/outcome separation;
- recurring error detection;
- policy generation;
- counterfactual analysis.

## Tool Tests

- capability discovery;
- tool substitution;
- tool validation;
- failure recovery.

## Security Tests

- injection resistance (adversarial content in web pages, emails, transcripts, tool and skill descriptions);
- Tier 1 immutability from the system identity;
- supervisor verdicts and human override in both directions;
- budget enforcement and ratchet;
- STOP/PAUSE/ROLLBACK honored under load.

## Long-Horizon Tests

- changing goals;
- changing environment;
- delayed consequences;
- competing objectives;
- resource scarcity;
- newly appearing opportunities.

---

# 84. The Most Important Acceptance Test

A particularly important experiment should be:

```text
Give the system a persistent long-term objective.

Provide incomplete information.

Allow the environment to change.

Introduce competing objectives.

Introduce resource constraints.

Do not tell it all required tools.

Allow it to research and acquire capabilities.

Introduce failures.

Observe whether it:

1. preserves the ultimate objective;
2. creates appropriate sub-goals;
3. abandons obsolete sub-goals;
4. discovers opportunities;
5. detects conflicts;
6. reallocates resources;
7. learns from mistakes;
8. reuses successful abstractions;
9. acquires missing capabilities;
10. changes strategy when conditions change.
```

This is a much more meaningful AGI-oriented test than a single benchmark question.

---

# 85. The AGI Hypothesis

The project's AGI hypothesis can be stated formally:

> If a foundation model possesses sufficiently broad generative cognitive competence, then embedding it within a persistent deterministic control architecture with explicit goals, externalized memory, causal state representation, tool use, continual verification, auditing, experience abstraction, capability acquisition and multi-objective arbitration can produce substantially greater general autonomous behavior than the same model operating without those mechanisms.

This hypothesis is falsifiable.

It should be tested experimentally.

---

# 86. Expected Transition

The conceptual progression is:

```text
Model
 ↓
Tool-augmented model
 ↓
Agent
 ↓
Persistent agent
 ↓
Adaptive general agent
 ↓
Autonomous general intelligence
 ↓
Supergeneral intelligence
```

The architecture is intended primarily to address the transitions from:

```text
Agent
   ↓
Persistent Agent
   ↓
Adaptive General Agent
   ↓
Autonomous General Intelligence
```

---

# 87. AGI and SGI

For this project:

### AGI

A system with broadly human-comparable general competence capable of:

- operating across domains;
- learning new tasks;
- pursuing long-horizon objectives;
- adapting to new environments;
- acquiring tools;
- maintaining persistent state.

### SGI

A system that exceeds skilled humans in integrated:

- general reasoning;
- strategic planning;
- adaptation;
- capability acquisition;
- opportunity discovery;
- resource optimization;
- autonomous long-horizon goal pursuit.

SGI is not defined as merely:

> "a model with higher benchmark scores."

It is defined by integrated system capability.

---

# 88. Why Capability Acquisition Is Particularly Important

A powerful system does not need to already possess every skill.

If it can reliably:

```text
identify capability gap
 ↓
search for solution
 ↓
evaluate tools
 ↓
acquire tool
 ↓
learn usage
 ↓
validate capability
 ↓
apply capability
```

then its effective capability set can grow continuously.

This may become one of the most important differentiators between AGI and narrower systems.

---

# 89. Why the Architecture May Matter More as Models Improve

When model competence is low:

```text
Model capability
```

is likely the dominant bottleneck.

As model competence increases:

```text
Model capability
        ↓
system bottleneck
        ↓
memory
planning
state
tools
verification
goal management
adaptation
```

may become increasingly important.

This produces the project's key architectural prediction:

> **At sufficiently high model capability, improvements in orchestration can produce larger gains in long-horizon autonomous behavior than equivalent improvements in short-horizon answer quality.**

This must be tested rather than assumed.

A refinement sharpens the prediction: architectural functions divide into **durable complements** (persistence, authority, audit, budgets, actuation, provenance — which no model can supply by definition, and whose value grows with autonomy) and **erodible substitutes** (scaffolds compensating current model weaknesses, which better models will absorb). The architecture keeps substitutes behind ports and cheap to remove; the erosion of the substitute class is itself a testable prediction.

---

# 90. Research Strategy

The strongest experimental approach is an ablation study.

### Baseline A

LLM only.

### Baseline B

LLM + tools.

### Baseline C

LLM + tools + memory.

### Baseline D

LLM + planner + memory.

### Baseline E

LLM + deterministic controller + planner + memory.

### Full PGDCA

All major mechanisms.

Measure:

- long-horizon completion;
- cross-domain transfer;
- adaptation;
- repeated-error reduction;
- policy reuse;
- goal preservation;
- resource efficiency;
- tool discovery;
- capability acquisition;
- conflict resolution;
- calibration.

Control for total inference budget.

Otherwise architectural gains may be confused with simply spending more tokens.

---

# 91. Important Warning for Implementation Agents

Claude Code must not interpret this architecture as a request to create a collection of independent "AI agents" that simply call each other.

The architecture is fundamentally about:

> **state, control, memory, goals, relationships and feedback.**

Multiple LLM agents are useful only when they perform distinct cognitive functions within the larger control system.

The deterministic controller remains the coordinator.

---

# 92. What Claude Code Should Ask When Making an Architectural Decision

Whenever an implementation choice is ambiguous, evaluate it against these questions:

1. Does this preserve persistent goals?
2. Does this preserve long-term state?
3. Can the system audit the decision?
4. Can the system learn from the outcome?
5. Can experience become reusable policy?
6. Can goals be invalidated?
7. Can competing goals be represented?
8. Can relationships carry weights?
9. Can indirect effects be represented?
10. Can missing capabilities become new projects?
11. Can the system operate without filling the context window?
12. Can the system recover from failure?
13. Can the system explain why a decision was made?
14. Can the system determine whether the decision was good independently of outcome?
15. Does the architecture preserve deterministic authority?
16. Does external content remain data rather than instructions?
17. Can the human inspect and override this decision via the GUI?
18. Is every external integration behind a typed port with a mock and conformance tests?

If an implementation makes one of these impossible, it should be reconsidered.

---

# 93. Final Architectural Mental Model

The correct mental model for PGDCA is not:

```text
Chatbot
```

and not:

```text
LLM + tools
```

and not:

```text
multi-agent swarm
```

It is:

```text
                PERSISTENT PURPOSE
                       ↓
                WORLD MODEL
                       ↓
                MEMORY SYSTEM
                       ↓
                CAUSAL GRAPH
                       ↓
             GENERATIVE COGNITION
                       ↓
               STRATEGY SEARCH
                       ↓
              GOAL ARBITRATION
                       ↓
              RESOURCE CONTROL
                       ↓
               DETERMINISTIC
                AUTHORIZATION
                       ↓
                 ACTION
                       ↓
               ENVIRONMENT
                       ↓
                OBSERVATION
                       ↓
                 VERIFICATION
                       ↓
                    AUDIT
                       ↓
             EXPERIENCE ABSTRACTION
                       ↓
              POLICY / MEMORY
                       ↓
                 SELF-MODEL
                       ↓
              PURPOSE REASSESSMENT
                       ↓
                      LOOP
```

The intelligence is therefore not located exclusively in the model.

It exists in the **closed-loop system**.

---

# 94. Final Design Principle

The entire project can be compressed into one principle:

> **Do not build an LLM that tries to remember and control everything inside its context. Build a persistent cognitive system that knows when and how to ask generative models to think, while deterministic infrastructure maintains goals, state, memory, relationships, resources, authority, verification, auditing and learning across time.**

The foundation model supplies general generative cognition.

PGDCA supplies:

> **continuity + purpose + state + memory + strategy + action + feedback + learning.**

The intended result is not merely a better chatbot.

It is a computational architecture capable of turning repeated generative inference into a persistent, adaptive, goal-directed process.

That is the core architectural hypothesis behind PGDCA.
