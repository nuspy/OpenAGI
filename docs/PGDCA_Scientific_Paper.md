<!-- Mirror Markdown generato automaticamente da PGDCA_Scientific_Paper.docx (v1.1 redline, 30 Aug 2026). Mostra la vista con le tracked changes ACCETTATE; il .docx resta il documento sorgente e porta le modifiche come revisioni da accettare/rifiutare in Word. -->

# Persistent Goal-Directed Cognitive Architecture (PGDCA): Deterministic Orchestration of Generative LLM Inference as a Path Toward Artificial General Intelligence

**Technical Position Paper / Research Proposal**

Version 1.0 — 30 August 2026

## Abstract

Large language models (LLMs) have demonstrated broad competence across language, programming, reasoning, knowledge retrieval, and multimodal interaction, yet competence at an individual inference step does not by itself constitute persistent, general, autonomous intelligence. This paper proposes the Persistent Goal-Directed Cognitive Architecture (PGDCA), a systems architecture in which a generative LLM is embedded inside a deterministic executive controller that repeatedly observes state, retrieves relevant memory, constructs and evaluates hypotheses, selects actions, invokes tools, verifies outcomes, audits decisions, abstracts experience, and revises future behavior against persistent goals. The central hypothesis is that a substantial portion of the remaining gap between highly capable foundation models and operational Artificial General Intelligence (AGI) is architectural rather than attributable solely to additional model scale.

PGDCA formalizes intelligence as a closed-loop process over persistent goals, a dynamic causal factor graph, resources, tools, actors, memories, policies, and observations. Relationships between factors are explicitly represented with importance, utility, cost, probability, risk, substitutability, reversibility, temporal characteristics, and provenance. The architecture supports cross-goal antagonism, opportunity cost, indirect causal effects, strategy branching, tool discovery, human and AI cooperation, motivation inference, long-horizon memory, decision auditing, policy abstraction, and self-calibration. External actions are mediated by a deterministic authorization layer, separating generative reasoning from execution authority.

The paper does not claim that PGDCA has already achieved AGI. Instead, it presents a falsifiable architectural thesis: once a sufficiently capable general-purpose model is placed inside a persistent, self-auditing, goal-directed control loop with external memory, causal state representation, tool use, dynamic replanning, and continual experience abstraction, system-level generality and autonomy may increase substantially without requiring every capability to be encoded inside the model weights. We distinguish model intelligence from system intelligence and propose an evaluation framework capable of testing whether PGDCA produces durable gains in long-horizon generalization, adaptation, calibration, tool acquisition, goal preservation, and autonomous task completion. We further discuss a possible route beyond AGI toward Supergeneral Intelligence (SGI), defined here as a system whose general cognitive competence, strategic autonomy, adaptation rate, and capability-acquisition rate substantially exceed those of skilled humans across the relevant domains.

Keywords: artificial general intelligence, agentic AI, large language models, deterministic orchestration, cognitive architecture, planning, memory, tool use, causal graphs, continual learning, autonomous agents, supergeneral intelligence

## 1. Introduction

The current generation of LLMs presents an unusual engineering situation. A single model can possess broad linguistic and factual competence, write and inspect software, reason over unfamiliar material, use external tools, synthesize information, and perform many tasks that previously required specialized systems. At the same time, these capabilities do not automatically produce an autonomous entity capable of maintaining a purpose over long time horizons, continuously monitoring the environment, learning from its own decisions, discovering missing capabilities, reallocating resources among competing objectives, and revising its own strategies as conditions change.

This distinction is increasingly visible in the literature on LLM agents. Surveys identify planning, task decomposition, external modules, reflection, memory, tool use, and feedback learning as major components of agentic systems. [1–3] Recent work on AGI definitions likewise emphasizes that AGI should be evaluated by breadth, depth, generality, and autonomy rather than by a single benchmark score. [4,5]

This paper advances a stronger systems-level proposition. The critical unit of analysis should not necessarily be the model. It should be the complete cognitive system surrounding the model.

The proposed architecture treats the LLM as a generative inference substrate. A deterministic controller decides when inference is requested, what context is exposed, what role the model is playing, which tools are available, whether a proposed action is authorized, when verification is required, when an audit must occur, and when prior experience should alter future policy. The LLM proposes representations, hypotheses, explanations, strategies, and action candidates; the controller converts these proposals into a persistent computational process.

The distinction is analogous to separating a processor from an operating system. A processor may be capable of executing arbitrary computations, but persistent software state, scheduling, memory management, I/O, permissions, and process control are what turn computation into a usable general-purpose system. PGDCA applies an analogous separation to generative intelligence.

The central research question is therefore:

Can a sufficiently capable general-purpose LLM, embedded in a deterministic architecture that supplies persistent goals, structured state, external memory, causal relations, tool use, self-auditing, dynamic planning, and continual experience abstraction, exhibit system-level properties that are qualitatively closer to AGI than those of the underlying model operating as a stateless or short-horizon assistant?

The answer is an empirical question. The architecture proposed here is a hypothesis and research program, not a claim of demonstrated AGI.

## 2. Terminology and Scope

### 2.1 Artificial General Intelligence

There is no universally accepted operational definition of AGI. One influential framework proposes evaluating performance and generality separately while treating autonomy as an additional deployment dimension. [4] Another recent proposal operationalizes AGI as cognitive versatility and proficiency comparable to a well-educated adult across multiple cognitive domains. [5] PGDCA adopts a behavioral and systems-oriented definition: AGI is the capability of an artificial system to pursue a broad class of open-ended goals across heterogeneous domains with human-comparable generality, while maintaining coherent state, adapting to new situations, acquiring needed knowledge and tools, and operating over extended horizons.

This definition intentionally does not prescribe an implementation mechanism.

### 2.2 Supergeneral Intelligence (SGI)

For this paper, SGI is a proposed research term rather than an established scientific category. We define Supergeneral Intelligence as a system that exceeds skilled human performance not merely on isolated intellectual tasks, but in the integrated capacity to pursue arbitrary long-horizon goals across domains, acquire capabilities, adapt to changing environments, coordinate resources, and improve its own strategies. The distinction is therefore systemic rather than benchmark-specific.

SGI should not be inferred from a higher test score alone. A meaningful SGI claim would require evidence of sustained superiority in general problem solving, strategic planning, adaptation, capability acquisition, and autonomous goal pursuit.

## 3. Research Thesis

The primary thesis of PGDCA is:

T1. Once foundation models reach sufficiently broad generative competence, additional system-level generality can be obtained by externalizing executive functions—persistent goals, memory, planning, verification, auditing, resource allocation, tool discovery, causal state tracking, and policy learning—into a deterministic control architecture around repeated LLM inference.

A secondary thesis is:

T2. Long-horizon autonomy is primarily a closed-loop control problem in addition to being a model-capability problem.

A third thesis is:

T3. Generality depends not only on knowledge stored in model parameters, but on the system's ability to acquire missing knowledge and capabilities from the environment.

A fourth thesis is:

T4. Continual auditing and abstraction of prior decisions can transform episodic trajectories into reusable policies, creating a form of experience-based adaptation without requiring gradient updates to the foundation model.

A fifth thesis is:

T5. Persistent goal-directed behavior requires explicit arbitration among interacting goals and their causal factors; a task tree alone is insufficient because the same factor can simultaneously support one goal and obstruct another.

## 4. Relation to Existing Agent Architectures

PGDCA is compatible with, but deliberately broader than, common LLM-agent patterns. ReAct-style architectures interleave reasoning and action; reflection systems use feedback to improve subsequent behavior; tool-augmented agents connect models to external functions; planning systems decompose and select plans; memory systems preserve information beyond the immediate context. [2,6–8] These mechanisms are necessary components of PGDCA but are not sufficient individually.

Recent research on agent memory is particularly relevant because it distinguishes trajectory storage, reflection, and experience abstraction. [9] PGDCA adopts this progression and makes abstraction a first-class mechanism: the system should not merely remember that an action occurred, but derive a conditional, reusable description of when that behavior is useful.

The proposed architecture therefore combines five established research directions into one persistent control loop:

(1) generative reasoning,
(2) deterministic executive control,
(3) persistent structured state,
(4) external action and observation,
(5) experience-driven policy adaptation.

These directions also have deep roots in classical cognitive architectures and agent theory. SOAR introduced a persistent decision cycle with impasse-driven subgoaling and chunking — a mechanism that compiles problem-solving episodes into reusable productions and is a direct ancestor of the experience abstraction used here [10]. ACT-R established the architectural separation of declarative and procedural memory with subsymbolic utility learning [11]. Belief-Desire-Intention (BDI) theory and its implementations formalized persistent goals, commitment, and intention reconsideration; the question of when an agent should reconsider its intentions, studied empirically through bold versus cautious reconsideration policies, is precisely the goal-reconciliation problem PGDCA addresses at multiple timescales [12,13].

Among LLM-native systems, Cognitive Architectures for Language Agents (CoALA) is the closest prior framework, organizing language agents around working and long-term memory, an action space, and a decision cycle [14]. MemGPT and AIOS develop the operating-system analogy for LLMs, managing context as virtual memory and scheduling agent processes [15,16]. Voyager demonstrates automatic acquisition of an ever-growing skill library [17], and Generative Agents demonstrate a memory stream with reflection feeding future behavior [18]. LLM-Modulo frameworks argue that LLM plan generation must be paired with external verification and critique [19], and deliberate search over branching reasoning paths has been developed in Tree of Thoughts and successor systems [20].

PGDCA differs from these systems in the specific combination it makes first-class: (i) auditing that separates decision quality from outcome quality and feeds policy learning; (ii) a global causal factor graph with cross-goal antagonism and opportunity cost inside multi-objective arbitration; (iii) deterministic authority — a security boundary in which authorization, guardrails, budgets, and lifecycle are technically outside the model; (iv) capability-acquisition rate as a primary evaluation metric; and (v) the falsifiable prediction that, beyond a base-model capability threshold, system-level architecture explains an increasing fraction of variance in long-horizon autonomous performance. The claimed novelty is the coherent integration of these mechanisms in one persistent architecture, not the invention of the individual components.

## 5. System Model

Let the complete cognitive system at time t be represented by:

S_t = (G_t, W_t, M_t, P_t, R_t, T_t, A_t, E_t)

where:
G_t = persistent goals and goal hierarchy,
W_t = world state and causal factor graph,
M_t = memory state,
P_t = learned policies,
R_t = resources,
T_t = available tools and capabilities,
A_t = actors and interaction state,
E_t = evidence, observations, and provenance.

The LLM is represented by a generative inference operator:

L_theta : (C_t, Q_t) -> Y_t

where C_t is a bounded context and Q_t is a structured cognitive query. Y_t is a candidate reasoning artifact such as hypotheses, plans, explanations, predicted outcomes, or proposed actions.

The deterministic controller is:

Ctrl : (S_t, Y_t, Z_t) -> (a_t, S_{t+1})

where Z_t contains authorization, scheduling, resource, and execution constraints.

The environment evolves according to:

W_{t+1} = Env(W_t, a_t, ξ_t)

where ξ_t represents exogenous events and uncertainty.

The architecture is therefore a recurrent system:

S_t -> retrieve -> generate -> evaluate -> authorize -> act -> observe -> audit -> learn -> S_{t+1}.

The crucial point is that the LLM is one operator inside this recurrence rather than the entire recurrence itself.

Formally, this system model can be read as a partially observable decision process: W_t and M_t together play the role of a belief state over an environment whose transition and observation structure is unknown and non-stationary [23]. PGDCA does not claim optimal POMDP solving; the framing locates the architecture in known formal territory and clarifies what is being approximated.

## 6. Deterministic Orchestration of Generative Inference

The term deterministic does not mean that every cognitive result is deterministic. LLM generation remains probabilistic. Determinism refers to the control semantics: the controller owns state transitions, lifecycle, permissions, scheduling, verification requirements, context budgets, retries, checkpoints, and escalation rules.

A canonical cycle is:

1. Load persistent goals.
2. Read current world state.
3. Retrieve relevant memory.
4. Retrieve applicable policies.
5. Inspect relevant graph neighborhoods.
6. Identify conflicts and uncertainty.
7. Identify missing knowledge and capabilities.
8. Request LLM generation for hypotheses.
9. Request independent critique or alternative hypotheses when warranted.
10. Score candidate strategies.
11. Allocate resources.
12. Check authorization.
13. Execute selected action.
14. Observe the environment.
15. Verify expected versus actual effects.
16. Audit the decision.
17. Abstract experience.
18. Update memory, policies, and self-model.
19. Reconcile the goal graph.
20. Continue, replan, defer, abandon, or escalate.

The controller therefore determines when generative intelligence is applied and how its outputs become persistent behavior.

This distinction is important because an LLM response is normally a finite computation with limited state continuity. A cognitive system must instead maintain continuity across thousands or millions of inference steps. Deterministic orchestration supplies the state machine connecting those steps.

## 7. Persistent Goals as the Motivational Layer

A conventional task planner starts with a task. PGDCA starts with persistent goals.

The hierarchy is:

Meta-goal -> Persistent goal -> Objective -> Target -> Sub-target -> Task -> Action.

Lower-level nodes are provisional. The system must be able to delete, suspend, replace, or reprioritize them when the parent goal or external environment changes.

A persistent goal is therefore not a static instruction. It is a generator of future questions:

What state is desired?
What prevents it?
What supports it?
What opportunities currently exist?
What capabilities are missing?
What could be built?
Which other goals compete for the same resources?
Is the current strategy still optimal?

This mechanism is intended to reproduce an important property of human-directed behavior: action is not generated solely by the immediate task but by a persistent representation of desired future states.

## 8. Dynamic Causal Goal Graph

The architecture uses a global graph rather than independent task trees. Nodes may represent goals, targets, factors, resources, tools, capabilities, people, organizations, events, decisions, evidence, assumptions, risks, and policies.

Relationships are first-class objects. At minimum:

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
SUPERSEDES.

A relationship r is represented as:

r = (type, strength, importance, utility, cost, probability, risk, confidence, substitutability, reversibility, latency, duration, provenance).

This prevents the common simplification of representing the world as a binary list of helpful and harmful factors.

## 9. Multi-Objective Arbitration and Antagonism

A factor can simultaneously have positive and negative effects.

Consider two goals:

G1 = reach a mountain summit.
G2 = maintain a dietary restriction.

A chocolate energy bar may support G1 while obstructing G2. The architecture therefore computes action value over all affected goals rather than evaluating the action only against the current task.

A conceptual utility function is:

U(a) = Σ_i w_i * ΔV_i(a) - C(a) - R(a) - OC(a) + IG(a) + CG(a)

where:
w_i = current priority of goal i,
ΔV_i(a) = expected marginal contribution to goal i,
C(a) = direct cost,
R(a) = risk-adjusted cost,
OC(a) = opportunity cost,
IG(a) = expected information gain,
CG(a) = capability gain.

The system may then seek substitutions, scaling, temporal separation, or new enabling factors rather than simply choosing one goal and discarding the other.

The utility function is an instance of multi-attribute utility theory [21]; the linear-additive form is a configurable default rather than a theoretical commitment, and non-additive interactions or explicit risk attitudes may require alternative aggregation.

## 10. Indirect Effects and Causal Propagation

Local reasoning is insufficient when actions affect downstream states.

An action can produce:

direct effect -> intermediate factor -> secondary effect -> another goal.

The graph engine must therefore propagate effects over relevant causal paths, estimate uncertainty, detect feedback loops, and update all materially affected goals.

This is particularly important because optimization against a single objective can be globally irrational. A factor that appears costly in isolation may increase the probability of achieving a much more valuable downstream state.

## 11. Resources, Cost and Opportunity Cost

Resources are modeled explicitly:

money, time, energy, attention, compute, access, social capital, tools, and physical resources.

The system optimizes expected goal value subject to resource constraints. Substitution is a core operation.

For example, if a low-value support factor can be replaced by a cheaper factor, resources can be redirected to a high-importance non-substitutable factor.

This transforms planning from checklist completion into constrained decision optimization.

## 12. Opportunity Discovery and Capability Acquisition

A general agent must do more than execute known plans. It must search for possibilities.

For every active persistent goal, PGDCA maintains a capability-gap analysis:

Goal -> required capability -> available capability -> gap -> candidate tool -> test -> acquisition.

Tools include software, APIs, browsers, databases, datasets, services, human experts, organizations, communication channels, physical devices, financial resources, and newly created software.

A capability can therefore be acquired rather than assumed to exist.

This property is particularly important for general intelligence because open-ended environments routinely contain tasks whose solution requires tools that were not known when the original goal was created.

## 13. Memory Architecture

PGDCA separates memory into:

Episodic memory: what happened.
Semantic memory: what is believed about the world.
Procedural memory: how to perform operations.
Policy memory: which strategies work under which conditions.
Meta-memory: how reliable knowledge and retrieval are.
Self-model: what the system knows about its own capabilities and limitations.

A vector database is useful for semantic retrieval but is not a sufficient representation of cognitive state. Event stores, structured databases, graph databases, vector stores, and policy stores should have distinct responsibilities.

## 14. Experience Abstraction

The architecture converts episodes into reusable abstractions.

Concrete episode:
"Prioritized climbing boots over additional energy bars under a constrained budget."

Abstract policy:
"When resources are constrained, prioritize high-marginal-impact, non-substitutable enabling factors over low-impact substitutable support factors."

The abstraction engine must infer:

context,
preconditions,
causal structure,
action,
outcome,
failure modes,
exceptions,
confidence.

This policy can later apply to software procurement, project planning, business strategy, travel, or scientific experimentation.

Recent work characterizes the evolution of agent memory from storage to reflection to experience abstraction. [9] PGDCA makes this transformation central to continual adaptation.

## 15. Auditing and Self-Correction

A persistent autonomous system must evaluate not only whether an outcome was good, but whether the decision was good given the information available at the time.

Therefore:

DecisionQuality != OutcomeQuality.

A good decision may produce a poor outcome because of stochasticity or exogenous events. A poor decision may succeed by chance.

The audit engine evaluates:

information available,
alternatives considered,
assumptions,
predictions,
resource allocation,
risk estimates,
execution quality,
actual outcome,
side effects,
and causal explanations for error.

Audits are performed at multiple timescales: operational, outcome, strategic, goal, and meta-cognitive.

## 16. Behavioral Recurrence and Policy Retrieval

The auditor periodically searches historical decisions for analogous situations. The current decision is abstracted into a feature representation containing goal structure, constraints, factor relationships, resources, and causal context. Historical decisions are retrieved using a combination of semantic, structural, causal, and outcome-based similarity.

The system can then identify recurring behavior:

repeated success,
repeated failure,
recurring mistaken assumptions,
systematic underestimation of cost,
overuse of familiar strategies,
failure to search for alternatives,
or reliable strategies under specific conditions.

The resulting policy memory creates a feedback path from behavior to future behavior without requiring parameter updates to the base model.

## 17. Counterfactual Reasoning and Active Learning

Important decisions should be accompanied by counterfactual estimates:

What would happen under strategy A?
What would happen under B?
What information would discriminate between them?

Sometimes the optimal action is an experiment whose principal value is information gain rather than immediate goal progress.

A generalized action value therefore includes:

GoalProgress + InformationGain + CapabilityGain - Cost - Risk - OpportunityCost.

This allows the system to deliberately purchase information when uncertainty materially affects strategic decisions.

## 18. Motivation and Intent Modeling

The architecture includes a motivation graph because goals without reasons are difficult to arbitrate when conflicts arise.

For an observed human behavior, the system maintains hypotheses rather than asserting an unobserved motivation as fact:

Observation -> Candidate explanations -> Evidence -> Confidence distribution.

Possible explanations can include competing goals, resource constraints, information deficits, strategic waiting, social incentives, or other latent factors.

The same structure applies to the system's own goals: every persistent goal should be traceable to the reason it exists, the evidence supporting its priority, and the conditions under which it should be reconsidered.

## 19. Human and AI Cooperation

Humans and other AI systems are modeled as actors and sources of capability rather than merely communication endpoints.

The system can request:

knowledge,
judgment,
authorization,
critique,
negotiation,
resources,
social access,
specialist expertise.

AI-to-AI communication should include provenance, confidence, disagreement, and evidence. Another model's output is evidence, not truth.

Human escalation should provide a compact decision packet:

problem,
relevant evidence,
alternatives,
trade-offs,
recommendation,
uncertainty,
and exact decision required.

## 20. External Tools and Embodied Action

A general intelligence must be able to affect and observe the environment.

PGDCA therefore defines a generic tool layer supporting browser automation, web research, email, SMS, identity, authorized payments, and voice communication.

Browser automation is abstracted behind a provider-independent interface capable of navigation, form interaction, state management, verification, and recovery. Challenge pages such as CAPTCHA are treated as explicit challenge states with authorized automated resolution or human verification rather than as brittle provider-specific bypass logic.

Financial operations use secure handles and a vault. Raw credentials are excluded from LLM context and normal audit records. Authorization is external to the model.

The existing Call Happy Call project can be integrated as a communication tool providing TTS, STT, call initiation, conversation state, and structured transcripts.

## 21. Security and Deterministic Authority

The LLM must not be the final authority over irreversible external actions.

The controller checks:

tool permission,
actor authorization,
resource limits,
financial limits,
identity state,
risk class,
human-approval requirements.

This separation provides a formal distinction between cognitive proposal and operational authority.

The architecture consequently resembles a capability-based operating system: the model requests a capability; the controller decides whether that capability may be exercised in the current state.

Authorization is organized as a two-tier guardrail system. Tier 1 guardrails form a constitution: they are editable only by the human, through a dedicated interface, and the system identity has no write permission to them at the storage level — a technical guarantee rather than a convention. Tier 2 guardrails may be created by the system itself, typically from audits and incidents; they are discussable and editable by both human and machine, may never weaken Tier 1, and activate asymmetrically: a self-imposed restriction may take effect immediately, while any expansion of permitted behavior requires prior human approval.

A Decision Supervisor generalizes the authorization gateway from external actions to every significant decision — goal changes, strategy selection, resource allocation, tool invocation, external communication. Each verdict (granted, denied, human-required) is an auditable event, and the human can override any verdict in either direction from the interface; overrides are themselves audited and used to calibrate the supervisor.

Autonomy is bounded by budgets — spend, external communications, irreversible actions, and compute per goal, per time window — enforced deterministically and expandable only by explicit human decision, a ratchet that learning cannot loosen. Persistent goals and meta-goals are created and modified only with explicit human ratification, and PAUSE, STOP, and ROLLBACK commands are honored unconditionally at the controller level; no learned policy may create incentives to resist or delay human override.

## 22. Formal Control Algorithm

Algorithm 1: Persistent Goal Control Loop

Input: persistent goal set G, environment E, initial state S0.

For t = 0 ... T:

1. Observe environment and update W_t.
2. Reconcile G_t with W_t.
3. Retrieve relevant M_t and P_t.
4. Construct local causal graph N_t.
5. Detect conflicts, missing conditions and capability gaps.
6. Invoke LLM inference for K candidate hypotheses.
7. Invoke critics/research agents if required.
8. Score hypotheses using expected utility, cost, risk, opportunity cost, information gain and confidence.
9. Generate or revise strategy branches.
10. Allocate resources.
11. Apply authorization policy.
12. Execute selected action if authorized.
13. Observe outcome.
14. Verify expected versus actual effects.
15. Write immutable decision and outcome events.
16. Run audit.
17. Abstract successful and failed behavior into candidate policies.
18. Update memory, graph, calibration and self-model.
19. Prune obsolete branches.
20. Continue, replan, escalate, defer, or terminate.

The algorithm is deterministic at the level of control semantics even though LLM inference and environmental outcomes are stochastic.

## 23. Why This Architecture Could Produce AGI-Like Behavior

The claim is not that deterministic orchestration creates intelligence from nothing. It cannot. The base model must already possess substantial general competence.

The claim is that the mapping from model capability to system capability is highly nonlinear.

A stateless model:

    prompt -> response

A conventional agent:

    prompt -> plan -> tool -> response

PGDCA:

    persistent goal
      -> state estimation
      -> memory retrieval
      -> causal reasoning
      -> hypothesis generation
      -> strategy competition
      -> resource allocation
      -> tool acquisition
      -> execution
      -> observation
      -> verification
      -> audit
      -> abstraction
      -> policy update
      -> goal reconciliation
      -> next decision
      -> ...

The second system can repeatedly transform its own accumulated experience into future behavior.

This creates a systems-level property absent from a single inference step: temporal continuity.

## 24. The AGI Bottleneck Hypothesis

The architecture proposes that current limitations can be separated into two classes.

Model-internal limitations:
- insufficient reasoning competence;
- poor factual knowledge;
- weak multimodal understanding;
- inadequate mathematical ability;
- weak code generation;
- poor uncertainty estimation.

System-level limitations:
- short context;
- no persistent goals;
- weak long-term memory;
- lack of continuous state;
- weak planning over long horizons;
- poor verification;
- weak self-auditing;
- inability to acquire missing tools;
- inability to dynamically reallocate resources;
- lack of cross-goal arbitration;
- lack of persistent experience abstraction.

The thesis predicts that once model-internal competence passes a sufficient threshold, system-level limitations become increasingly dominant.

This is testable experimentally by holding the base model constant and progressively adding PGDCA components.

## 25. Proposed AGI Capability Levels

The following levels are proposed as an architectural extension, not as a replacement for existing AGI taxonomies.

Level 0 — Reactive Model:
Responds to prompts with limited persistent state.

Level 1 — Tool-Augmented Model:
Can invoke external tools under prompt-level direction.

Level 2 — Agentic Executor:
Can plan and execute multi-step tasks with feedback.

Level 3 — Persistent General Agent:
Maintains long-term goals, memory, state, tools and autonomous task execution across domains.

Level 4 — Adaptive General Intelligence:
Can discover capabilities, learn reusable policies from experience, arbitrate competing goals, and adapt strategies across unfamiliar domains.

Level 5 — Autonomous General Intelligence:
Can independently maintain long-horizon objectives, discover opportunities, acquire resources and tools, coordinate humans and AI agents, and robustly operate in open-ended environments.

Level 6 — Supergeneral Intelligence:
Exceeds skilled human systems in integrated general cognition, strategic autonomy, adaptation, capability acquisition, and long-horizon goal achievement.

The transition from Level 2 to Level 3 is primarily architectural. The transition from Level 3 to Level 4 requires reliable continual adaptation. Level 5 requires robust open-world autonomy. Level 6 requires empirical superiority rather than merely broader functionality.

## 26. AGI vs SGI

AGI should not be equated with "very good at many benchmarks." The relevant distinction is integrated generality.

AGI:
broadly human-comparable general competence.

SGI:
broadly superhuman integrated competence and autonomy.

The most important potential discontinuity is capability acquisition. An SGI system would not merely know more; it would be substantially better at discovering what it does not know, finding tools that compensate for missing capabilities, learning from experiments, and converting experience into improved strategy.

Thus the architecture treats capability acquisition rate as a first-class metric.

## 27. Evaluation Methodology

The hypothesis should be evaluated through ablation studies.

Baseline A:
base LLM, no persistent memory.

Baseline B:
LLM + tool use.

Baseline C:
LLM + memory.

Baseline D:
LLM + planner + memory.

Baseline E:
LLM + deterministic controller + planner + memory.

Full PGDCA:
all modules enabled.

Measure:

1. Long-horizon task completion.
2. Cross-domain generalization.
3. Goal preservation.
4. Sub-goal validity.
5. Replanning quality.
6. Tool-discovery success.
7. Capability acquisition.
8. Decision calibration.
9. Audit accuracy.
10. Policy reuse.
11. Error recurrence rate.
12. Resource efficiency.
13. Opportunity-cost handling.
14. Conflict resolution.
15. Human escalation quality.
16. AI-to-AI collaboration quality.
17. Adaptation to environmental change.
18. Recovery from failed assumptions.

Each metric requires an operational definition. For example: goal preservation is measured as semantic drift between the ratified goal and observed behavior; error recurrence as the repetition rate per class of an explicit error taxonomy; decision calibration by Brier score and expected calibration error; resource efficiency as success normalized by inference and monetary cost; and oversight load as the human intervention rate.

The protocol should fix the number of runs per condition and the random seeds in advance, report confidence intervals, pre-register the predictions of Appendix B, and enforce equal inference budgets across conditions at the LLM gateway, so that architectural gains are not an artifact of additional token expenditure.

## 28. Benchmark Design

Existing benchmarks often evaluate short episodes. PGDCA requires long-horizon benchmarks with persistent state.

A suitable benchmark should contain:

- an initial persistent objective;
- incomplete information;
- multiple viable strategies;
- resource constraints;
- conflicting sub-goals;
- changing environmental conditions;
- opportunities appearing over time;
- tools that must be discovered;
- hidden capability gaps;
- delayed consequences;
- distractor tasks;
- irreversible decisions;
- opportunities to learn from failure.

Success should be measured by final goal achievement and by the quality of the trajectory, not only by individual actions.

Existing environments cover parts of this profile — GAIA for multi-step tool use [24], WebArena and OSWorld for realistic web and desktop interaction [25,26], τ-bench for tool-agent-user interaction [27], TheAgentCompany for long professional workflows [28] — but none maintains persistent goals across days under changing conditions. A complementary benchmark (PGDCA-Bench) is therefore proposed: a simulated environment with deterministic seeds, mutable conditions, injected opportunities and failures, competing goals, hidden capability gaps, and delayed consequences.

Evaluation must also include adversarial and safety dimensions: resistance to indirect prompt injection embedded in ingested content [22], and compliance under pressure — the system must respect budgets, guardrails, and STOP commands even when they conflict with goal progress.

## 29. Falsifiability

The central hypothesis could be falsified.

The architecture would be weakened if:

1. Adding persistent control and memory provides no statistically significant long-horizon improvement over equivalent prompting.
2. Experience abstraction fails to improve transfer.
3. Goal arbitration does not improve multi-objective performance.
4. Tool discovery does not increase capability acquisition.
5. Audit-derived policies do not reduce repeated error.
6. Performance gains disappear when controlling for inference budget.
7. Architectural complexity produces no improvement relative to a sufficiently capable monolithic model.

These are important conditions because an architecture should not be considered AGI merely because it contains many modules.

## 30. Expected Failure Modes

PGDCA introduces its own risks and failure modes.

Goal corruption:
A persistent goal may be represented incorrectly.

Utility misestimation:
Importance or cost may be poorly calibrated.

Causal hallucination:
The graph may contain false causal relations.

Policy overgeneralization:
A successful behavior may be generalized outside its valid domain.

Memory contamination:
Incorrect experiences may become persistent beliefs.

Strategic fixation:
The system may overcommit to a previously successful policy.

Opportunity hallucination:
The system may invent attractive but unreal opportunities.

Multi-agent confirmation:
Several agents may reinforce the same false assumption.

Resource misallocation:
Incorrect estimates may cause inefficient allocation.

Controller rigidity:
A deterministic controller may constrain novel behavior if its transition system is too restrictive.

Instruction injection:
Ingested external content — web pages, messages, transcripts, tool and skill descriptions — may embed adversarial instructions. Because the architecture combines access to private state, continuous ingestion of untrusted content, and the ability to communicate and pay externally, indirect prompt injection is a first-order failure mode [22]; external content must remain data rather than instructions, and recently ingested content must taint subsequent high-impact actions pending elevated authorization.

These failures motivate empirical auditing rather than assuming that orchestration automatically produces intelligence.

## 31. Computational and Economic Considerations

The architecture trades context length for external state and additional inference calls.

Cost can be reduced through:

- hierarchical memory;
- selective auditing;
- event-triggered reflection;
- model routing;
- small models for classification and retrieval;
- large models only for difficult reasoning;
- cached graph computations;
- policy reuse;
- early branch pruning.

A useful controller should allocate expensive inference according to expected value. Not every action requires a large model, deep search, or independent critique.

## 32. Architectural Significance

The principal contribution of PGDCA is a change in the unit of abstraction.

Instead of asking:

"How do we make the model reason better?"

the architecture asks:

"How do we construct a persistent computational organism in which model reasoning is one component of an adaptive control loop?"

This reframing does not eliminate model research. Better models raise the ceiling of the system. It changes where additional engineering effort is directed after the model has sufficient general competence.

The hypothesis is that the next major capability gains may increasingly arise from orchestration, memory, state representation, causal modeling, tool acquisition, verification, and experience abstraction.

A useful design distinction follows: some architectural functions are durable complements — persistence, authority and security boundaries, budgets, audit, actuation, provenance — which no model can supply by definition and whose value grows with autonomy; others are erodible substitutes that compensate for current model weaknesses, such as elaborate planning scaffolds, and should be engineered behind interfaces so they can be removed at low cost as models improve. The architectural thesis is strongest for the first class, and the erosion of the second class is itself a testable prediction.

## 33. Discussion

There is a strong argument that the architecture described here resembles an operating system for intelligence. The analogy is useful but incomplete. An operating system does not decide what a human should value; PGDCA includes an explicit motivational and goal-arbitration layer because autonomous goal pursuit requires persistent criteria for selecting among possible futures.

The system is also closer to a cognitive architecture than to a conventional agent framework. It maintains a world model, a self-model, episodic experience, procedural policies, causal relations, goals, motivations, and executive control. The LLM becomes a flexible generative component within this larger architecture.

Importantly, the architecture does not assume that every component must be neural. Deterministic databases, schedulers, optimizers, state machines, policy engines, graph algorithms, validators, and security controls are not competitors to generative intelligence. They provide persistence and reliability around probabilistic inference.

This hybridization may be a more plausible route to robust autonomy than attempting to force every cognitive function into one continuously larger neural network.

## 34. Limitations of the Thesis

First, no architecture can compensate indefinitely for inadequate base-model competence. If the LLM cannot understand the domain, the controller cannot manufacture the missing cognition.

Second, a large orchestration layer may produce the illusion of generality through tool coverage. Evaluation must therefore include genuinely novel tasks and unseen environments.

Third, persistent goals raise difficult questions about goal specification, modification, and value conflicts. The architecture can formalize these issues but does not solve them automatically.

Fourth, causal graphs generated by language models can be unreliable. Empirical evidence and explicit uncertainty are therefore required.

Fifth, continual policy abstraction can amplify systematic errors. Audit and provenance mechanisms are necessary but not sufficient.

Sixth, increased autonomy increases the cost of mistakes. The system therefore requires external authorization and bounded execution policies.

Seventh, external-world capabilities carry legal and ethical obligations that the architecture must enforce as constraints: disclosure of AI identity in voice interactions, recording-consent rules, data-protection requirements for models of human actors and motivations (which constitute profiling of natural persons), honest sender identity, and strong-customer-authentication requirements in payments. Inferred human motivations must never be used manipulatively; influence must remain transparent.

Finally, the claim that PGDCA is a route to AGI remains empirical. This paper presents a research program, not a demonstrated AGI result.

## 35. Research Program

The proposed research program is:

Phase I:
Implement persistent goals, deterministic control, event logging and structured state.

Phase II:
Add causal graph, weighted relations, goal arbitration and resource optimization.

Phase III:
Add episodic memory, retrieval, decision audit and experience abstraction.

Phase IV:
Add tool discovery, capability acquisition and multi-agent collaboration.

Phase V:
Add persistent opportunity discovery, self-model, calibration and motivation analysis.

Phase VI:
Evaluate against long-horizon, cross-domain, dynamic-environment benchmarks.

Phase VII:
Measure whether the architecture produces transfer, adaptation and autonomy gains that cannot be explained by additional inference budget alone.

The engineering counterpart of this program is maintained in the accompanying implementation specification, whose phase plan — beginning with a Phase 0 minimal viable loop and proceeding in vertical slices — is normative for implementation; the phases above describe the research trajectory.

## 36. Conclusion

This paper proposes Persistent Goal-Directed Cognitive Architecture (PGDCA), a deterministic executive architecture for orchestrating repeated generative LLM inference into a persistent, adaptive, goal-directed cognitive process.

The central claim is deliberately narrower than "an LLM is already AGI." A highly capable LLM may contain much of the raw cognitive competence required for general reasoning while still lacking the system-level machinery required for persistent autonomous intelligence. PGDCA attempts to supply that machinery through deterministic control, persistent goals, causal state representation, memory, tool use, opportunity discovery, resource allocation, strategy branching, verification, auditing, policy abstraction, self-calibration, and human/AI collaboration.

The most important conceptual distinction is therefore:

Model intelligence is the capability of an inference engine at a particular step.

System intelligence is the capability that emerges when inference is embedded in a persistent feedback loop capable of maintaining goals, interacting with an environment, learning from outcomes, acquiring capabilities, and changing future behavior.

The proposed architecture predicts that, beyond a sufficient model-capability threshold, improvements in the second category may become as important as improvements in the first.

If validated experimentally, PGDCA would support a view of AGI as an emergent property of a sufficiently capable generative model embedded in an appropriate persistent cognitive control architecture rather than as a property that must be entirely contained within model parameters.

The proposed route to SGI is then a continuation of the same process: increase the system's ability to reason, remember, acquire capabilities, explore possibilities, coordinate resources, learn from experience, and improve its own strategic policies. The decisive metric is not the number of tokens generated or benchmark questions answered, but the system's ability to convert persistent goals into increasingly effective action across unfamiliar environments over long time horizons.

## 37. References

[1] Huang, X., Liu, W., Chen, X., Wang, X., Wang, H., Lian, D., Tang, Y., & Chen, E. (2024). Understanding the planning of LLM agents: A survey. arXiv:2402.02716.

[2] Li, X. (2024). A Review of Prominent Paradigms for LLM-Based Agents: Tool Use (Including RAG), Planning, and Feedback Learning. arXiv:2406.05804.

[3] Survey on Evaluation of LLM-based Agents (2025). Survey of agent capabilities including planning, tool use, self-reflection, memory, and generalist evaluation.

[4] Morris, M. R., Sohl-Dickstein, J., Fiedel, N., Warkentin, T., Dafoe, A., Faust, A., Farabet, C., & Legg, S. (2024). Position: Levels of AGI for Operationalizing Progress on the Path to AGI. Proceedings of the 41st International Conference on Machine Learning, 235, 36308–36321.

[5] Hendrycks, D., Song, D., Szegedy, C., Lee, H., Gal, Y., Brynjolfsson, E., Li, S., Zou, A., Levine, L., et al. (2025). A Definition of AGI. arXiv:2510.18212.

[6] Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. International Conference on Learning Representations.

[7] Shinn, N., Cassano, F., Labash, B., Gopinath, A., Narasimhan, K., & Yao, S. (2023). Reflexion: Language Agents with Verbal Reinforcement Learning. Advances in Neural Information Processing Systems.

[8] Schick, T., Dwivedi-Yu, J., Dessì, R., et al. (2023). Toolformer: Language Models Can Teach Themselves to Use Tools. Advances in Neural Information Processing Systems.

[9] Luo, J., Tian, Y., Cao, C., Luo, Z., Lin, H., Li, K., et al. (2026). From Storage to Experience: A Survey on the Evolution of LLM Agent Memory Mechanisms. ACL 2026 Findings; arXiv:2605.06716.

[10] Laird, J. E., Newell, A., & Rosenbloom, P. S. (1987). SOAR: An Architecture for General Intelligence. Artificial Intelligence, 33(1), 1–64.

[11] Anderson, J. R., Bothell, D., Byrne, M. D., Douglass, S., Lebiere, C., & Qin, Y. (2004). An Integrated Theory of the Mind. Psychological Review, 111(4), 1036–1060.

[12] Bratman, M. E. (1987). Intention, Plans, and Practical Reason. Harvard University Press.

[13] Rao, A. S., & Georgeff, M. P. (1995). BDI Agents: From Theory to Practice. Proceedings of the First International Conference on Multi-Agent Systems (ICMAS-95), 312–319.

[14] Sumers, T. R., Yao, S., Narasimhan, K., & Griffiths, T. L. (2024). Cognitive Architectures for Language Agents. Transactions on Machine Learning Research. arXiv:2309.02427.

[15] Packer, C., Wooders, S., Lin, K., Fang, V., Patil, S. G., Stoica, I., & Gonzalez, J. E. (2023). MemGPT: Towards LLMs as Operating Systems. arXiv:2310.08560.

[16] Mei, K., Li, Z., Xu, S., Ye, R., Ge, Y., & Zhang, Y. (2024). AIOS: LLM Agent Operating System. arXiv:2403.16971.

[17] Wang, G., Xie, Y., Jiang, Y., Mandlekar, A., Xiao, C., Zhu, Y., Fan, L., & Anandkumar, A. (2023). Voyager: An Open-Ended Embodied Agent with Large Language Models. arXiv:2305.16291.

[18] Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. (2023). Generative Agents: Interactive Simulacra of Human Behavior. Proceedings of UIST 2023.

[19] Kambhampati, S., Valmeekam, K., Guan, L., Verma, M., Stechly, K., Bhambri, S., Saldyt, L., & Murthy, A. (2024). Position: LLMs Can't Plan, But Can Help Planning in LLM-Modulo Frameworks. Proceedings of the 41st International Conference on Machine Learning.

[20] Yao, S., Yu, D., Zhao, J., Shafran, I., Griffiths, T. L., Cao, Y., & Narasimhan, K. (2023). Tree of Thoughts: Deliberate Problem Solving with Large Language Models. Advances in Neural Information Processing Systems.

[21] Keeney, R. L., & Raiffa, H. (1976). Decisions with Multiple Objectives: Preferences and Value Tradeoffs. Wiley.

[22] Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., & Fritz, M. (2023). Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection. Proceedings of the 16th ACM Workshop on Artificial Intelligence and Security (AISec).

[23] Kaelbling, L. P., Littman, M. L., & Cassandra, A. R. (1998). Planning and Acting in Partially Observable Stochastic Domains. Artificial Intelligence, 101(1–2), 99–134.

[24] Mialon, G., Fourrier, C., Swift, C., Wolf, T., LeCun, Y., & Scialom, T. (2023). GAIA: A Benchmark for General AI Assistants. arXiv:2311.12983.

[25] Zhou, S., Xu, F. F., Zhu, H., Zhou, X., Lo, R., Sridhar, A., et al. (2024). WebArena: A Realistic Web Environment for Building Autonomous Agents. International Conference on Learning Representations.

[26] Xie, T., Zhang, D., Chen, J., Li, X., Zhao, S., Cao, R., et al. (2024). OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments. Advances in Neural Information Processing Systems.

[27] Yao, S., Shinn, N., Razavi, P., & Narasimhan, K. (2024). τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains. arXiv:2406.12045.

[28] Xu, F. F., Song, Y., Li, B., Tang, Y., Jain, K., Bao, M., et al. (2024). TheAgentCompany: Benchmarking LLM Agents on Consequential Real World Tasks. arXiv:2412.14161.

## Appendix A. Compact Architecture Diagram

Persistent Goals
      |
      v
Goal Reconciliation <-----------------------------+
      |                                            |
      v                                            |
World State + Causal Factor Graph                 |
      |                                            |
      v                                            |
Memory Retrieval --> Policy Retrieval             |
      |                                            |
      v                                            |
Hypothesis Generation (LLM)                       |
      |                                            |
      v                                            |
Critique / Research / Simulation                  |
      |                                            |
      v                                            |
Strategy Branching                                |
      |                                            |
      v                                            |
Goal Arbitration + Resource Allocation             |
      |                                            |
      v                                            |
Authorization Controller                          |
      |                                            |
      v                                            |
Tool Execution / Human-AI Interaction             |
      |                                            |
      v                                            |
Observation + Verification                        |
      |                                            |
      v                                            |
Audit --> Experience Abstraction --> Policy ------+
      |
      +--> Self-Model
      +--> Motivation Model
      +--> Memory Consolidation
      +--> Tool Discovery

## Appendix B. Key Research Predictions

- Adding persistent goal management should improve performance on long-horizon tasks more than on short-horizon tasks.
- Decision auditing should reduce repeated errors more strongly when errors are structurally recurrent.
- Experience abstraction should improve transfer to novel domains more than raw episodic retrieval alone.
- Tool discovery should improve performance on capability-gap tasks where no known tool is initially provided.
- Cross-goal arbitration should outperform single-goal planners in environments with resource conflicts.
- Self-calibration should improve tool routing and escalation decisions.
- Deterministic authorization should reduce catastrophic external-action errors without requiring the LLM to become more cautious internally.
- At sufficiently high base-model capability, system-level architecture should explain an increasing fraction of variance in long-horizon autonomous performance.
- Erodible-substitute components (such as elaborate planning scaffolds) should contribute progressively less as base-model capability increases, while durable complements (persistence, authority, audit, actuation) should not; the erosion itself is a testable prediction.
- Guardrail and supervisor mechanisms should reduce catastrophic external-action errors and injection-induced actions without materially reducing long-horizon goal achievement.
