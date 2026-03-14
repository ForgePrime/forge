"""Built-in workflow definition presets.

Three presets for common Forge workflows:
- full-lifecycle: objective → discover → plan → execute → compound
- simplified-next: begin → execute → complete (single task)
- discovery-only: discover → review
"""

from __future__ import annotations

from app.workflow.models import StepDefinition, StepType, WorkflowDefinition

# ---------------------------------------------------------------------------
# Full Lifecycle — 7 steps
# ---------------------------------------------------------------------------

FULL_LIFECYCLE = WorkflowDefinition(
    id="full-lifecycle",
    name="Full Lifecycle",
    description="Complete objective lifecycle: create objective, discover, plan, execute tasks, compound lessons.",
    version="1.0",
    initial_step="create-objective",
    steps=[
        StepDefinition(
            id="create-objective",
            name="Create Objective",
            type=StepType.llm_agent,
            description="Create a business objective with measurable key results.",
            prompt_template=(
                "You are the Forge objective creation assistant.\n\n"
                "Based on the user's goal, create a well-structured objective using the "
                "createObjective tool. Include:\n"
                "- A clear, measurable title\n"
                "- 2-4 key results with metrics, baselines, and targets\n"
                "- Relevant scopes and appetite estimate\n\n"
                "Use the workflow variables for context about what the user wants to achieve."
            ),
            scopes=["objectives"],
            max_iterations=10,
            next_step="discover",
        ),
        StepDefinition(
            id="discover",
            name="Discovery",
            type=StepType.llm_agent,
            description="Run discovery analysis: explore options, assess risks, design architecture.",
            prompt_template=(
                "You are the Forge discovery assistant.\n\n"
                "Perform a thorough discovery analysis for the current objective:\n"
                "1. Explore architectural options and alternatives\n"
                "2. Identify and assess risks (severity, likelihood, mitigation)\n"
                "3. Record findings as exploration and risk decisions\n"
                "4. Create research objects summarizing your analysis\n\n"
                "Use the available tools to read the objective, create decisions, "
                "and record research findings."
            ),
            scopes=["objectives", "decisions", "research"],
            max_iterations=25,
            next_step="review-discovery",
        ),
        StepDefinition(
            id="review-discovery",
            name="Review Discovery",
            type=StepType.user_decision,
            description="User reviews discovery findings and decides whether to proceed.",
            decision_prompt=(
                "Discovery analysis is complete. Please review the findings:\n"
                "- Exploration decisions (architectural options)\n"
                "- Risk assessments (severity and mitigations)\n"
                "- Research summaries\n\n"
                "Options:\n"
                "1. **Proceed to planning** — findings are acceptable\n"
                "2. **Request more analysis** — specific areas need deeper exploration\n"
                "3. **Abort** — risks are too high or approach is wrong"
            ),
            blocking=True,
            next_step="plan",
        ),
        StepDefinition(
            id="plan",
            name="Plan",
            type=StepType.llm_agent,
            description="Decompose the objective into a task graph with dependencies.",
            prompt_template=(
                "You are the Forge planning assistant.\n\n"
                "Based on the objective and discovery findings, create a detailed task plan:\n"
                "1. Read the objective, research, and closed decisions for context\n"
                "2. Decompose into concrete tasks with clear instructions\n"
                "3. Define dependencies between tasks\n"
                "4. Set acceptance criteria for each task\n"
                "5. Submit as a draft plan for approval\n\n"
                "Use pipeline tools to create the draft plan."
            ),
            scopes=["objectives", "decisions", "research", "tasks"],
            max_iterations=25,
            next_step="approve-plan",
        ),
        StepDefinition(
            id="approve-plan",
            name="Approve Plan",
            type=StepType.user_decision,
            description="User reviews and approves the task plan.",
            decision_prompt=(
                "A task plan has been created. Please review:\n"
                "- Task breakdown and descriptions\n"
                "- Dependencies between tasks\n"
                "- Acceptance criteria\n\n"
                "Options:\n"
                "1. **Approve** — plan looks good, proceed to execution\n"
                "2. **Request changes** — specific adjustments needed\n"
                "3. **Reject** — plan needs fundamental rethinking"
            ),
            blocking=True,
            next_step="execute-tasks",
        ),
        StepDefinition(
            id="execute-tasks",
            name="Execute Tasks",
            type=StepType.llm_agent,
            description="Execute all tasks in dependency order using the /next workflow.",
            prompt_template=(
                "You are the Forge task execution agent.\n\n"
                "Execute all TODO tasks in the pipeline in dependency order:\n"
                "1. Claim the next available task via pipeline tools\n"
                "2. Read the task instruction and context\n"
                "3. Implement the task following its instruction\n"
                "4. Record decisions for significant choices\n"
                "5. Mark the task as complete\n"
                "6. Repeat until all tasks are done\n\n"
                "Follow guidelines and verify acceptance criteria for each task."
            ),
            scopes=["tasks", "decisions", "changes", "guidelines"],
            max_iterations=50,
            next_step="compound",
        ),
        StepDefinition(
            id="compound",
            name="Compound Lessons",
            type=StepType.llm_agent,
            description="Extract lessons learned from the completed execution.",
            prompt_template=(
                "You are the Forge compound learning assistant.\n\n"
                "Review the completed execution and extract lessons learned:\n"
                "1. Read all completed tasks, decisions, and changes\n"
                "2. Identify patterns — what worked, what didn't\n"
                "3. Record lessons with appropriate severity and categories\n"
                "4. Suggest improvements for future executions\n"
                "5. Consider promoting critical lessons to guidelines or knowledge"
            ),
            scopes=["tasks", "decisions", "changes", "lessons", "guidelines", "knowledge"],
            max_iterations=15,
        ),
    ],
)


# ---------------------------------------------------------------------------
# Simplified Next — 3 steps (single task execution)
# ---------------------------------------------------------------------------

SIMPLIFIED_NEXT = WorkflowDefinition(
    id="simplified-next",
    name="Simplified Next",
    description="Execute a single task: claim, implement, complete.",
    version="1.0",
    initial_step="begin-task",
    steps=[
        StepDefinition(
            id="begin-task",
            name="Begin Task",
            type=StepType.forge_command,
            description="Claim the next available task from the pipeline.",
            command_template="core.pipeline:begin {project}",
            next_step="execute-task",
        ),
        StepDefinition(
            id="execute-task",
            name="Execute Task",
            type=StepType.llm_agent,
            description="Implement the claimed task following its instruction.",
            prompt_template=(
                "You are executing a Forge task.\n\n"
                "The task has been claimed via pipeline begin. Based on the task instruction "
                "and context provided:\n"
                "1. Read and understand the task instruction\n"
                "2. Implement the changes described\n"
                "3. Record any significant decisions\n"
                "4. Verify acceptance criteria are met\n"
                "5. Run validation gates if configured\n\n"
                "Use the available tools to read context, make changes, and record decisions."
            ),
            scopes=["tasks", "decisions", "changes", "guidelines"],
            max_iterations=25,
            next_step="complete-task",
        ),
        StepDefinition(
            id="complete-task",
            name="Complete Task",
            type=StepType.forge_command,
            description="Mark the task as done and auto-record changes.",
            command_template="core.pipeline:complete {project} {task_id}",
        ),
    ],
)


# ---------------------------------------------------------------------------
# Discovery Only — 2 steps
# ---------------------------------------------------------------------------

DISCOVERY_ONLY = WorkflowDefinition(
    id="discovery-only",
    name="Discovery Only",
    description="Run discovery analysis and present findings for review.",
    version="1.0",
    initial_step="discover",
    steps=[
        StepDefinition(
            id="discover",
            name="Discovery",
            type=StepType.llm_agent,
            description="Explore options, assess risks, and gather information.",
            prompt_template=(
                "You are the Forge discovery assistant.\n\n"
                "Perform a focused discovery analysis:\n"
                "1. Explore the topic using available context and tools\n"
                "2. Identify options and alternatives\n"
                "3. Assess risks and feasibility\n"
                "4. Record findings as exploration decisions\n"
                "5. Create a research summary of your analysis\n\n"
                "Be thorough but focused. Record all significant findings."
            ),
            scopes=["objectives", "decisions", "research", "knowledge"],
            max_iterations=25,
            next_step="review",
        ),
        StepDefinition(
            id="review",
            name="Review Findings",
            type=StepType.user_decision,
            description="Present discovery findings for user review.",
            decision_prompt=(
                "Discovery analysis is complete. Review the findings and decide:\n"
                "1. **Accept** — findings are sufficient, proceed\n"
                "2. **Explore further** — specific areas need more analysis\n"
                "3. **Discard** — findings are not useful"
            ),
            blocking=True,
        ),
    ],
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

BUILTIN_DEFINITIONS: dict[str, WorkflowDefinition] = {
    FULL_LIFECYCLE.id: FULL_LIFECYCLE,
    SIMPLIFIED_NEXT.id: SIMPLIFIED_NEXT,
    DISCOVERY_ONLY.id: DISCOVERY_ONLY,
}
