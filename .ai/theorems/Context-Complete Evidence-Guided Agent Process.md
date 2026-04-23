Theorem (Context-Complete Evidence-Guided Agent Process)

An AI-agent process is reliable if and only if the agent is not required to infer missing task-critical structure from its prior distribution, because every stage of the process provides, in time and in explicit form:

the relevant context,
the required level of detail,
the decomposition appropriate to the task,
the known ambiguities,
the testable success conditions,
the evidence produced by previous stages,
the hard constraints for the current action.

Formally, let:

S1, S2, ..., Sn be the ordered stages of the process
C_i be the context delivered to the agent at stage i
R_i be the task requirements at stage i
A_i be the ambiguity set known at stage i
E_i be the evidence produced at stage i
T_i be the testable conditions defined at stage i
O_i be the output produced at stage i
G_i be the gate for stage i

Then the process is sound only if, for every stage i:

Context completeness
C_i contains all task-relevant information required for stage i
Context sufficiency
C_i is sufficient for the agent to perform stage i without inventing missing structure
Timely delivery
C_i, R_i, A_i, and upstream evidence are delivered before O_i is produced
Ambiguity exposure
all unresolved ambiguities relevant to stage i are explicitly represented in A_i
Evidence continuity
E_i is derived from data, documents, code, or deterministic verification, and is propagated to later stages where relevant
Testability
every stage defines T_i such that O_i can be evaluated against explicit conditions
Gate discipline
O_i may influence later stages only if G_i is satisfied
Non-hallucinatory progression
if C_i is insufficient, the agent must stop or escalate, rather than complete the gap from priors

If any of the above fails, then downstream correctness is no longer guaranteed, and the process degrades into prior-driven inference rather than evidence-guided execution.



Theorem (Context-Complete Evidence-Guided Agent Process)

An AI-agent process is reliable only if, at every stage, the agent receives in time:

- all task-relevant context
- the right level of detail
- explicit ambiguities
- testable success conditions
- hard constraints
- evidence from previous stages

and only if:

- each stage output is testable
- each stage is gated
- missing critical context causes stop or escalation
- downstream stages consume evidence, not prior-based guesses

If any stage lacks task-critical information and the agent is still allowed to continue, the process degrades from evidence-guided execution into prior-substituted inference, and downstream correctness is no longer guaranteed.





Let S1..Sn be the ordered stages of an AI process.

For each stage i, let:
- C_i = context delivered to the agent
- R_i = requirements
- A_i = unresolved ambiguities
- E_i = evidence from prior stages
- T_i = testable conditions
- O_i = stage output
- G_i = stage gate

The process is sound only if for every i:

1. RequiredInfo(i) subset_of C_i
2. Suff(C_i, R_i, i) = true
3. O_i is derived from C_i, R_i, and E_<i
4. A_i is explicit and propagated until resolved
5. exists T_i such that Eval(O_i, T_i) is deterministic
6. O_i may propagate only if G_i = pass
7. Missing(C_i) implies Stop(i) or Escalate(i), not Guess(i)

Otherwise the process becomes prior-driven rather than evidence-guided.