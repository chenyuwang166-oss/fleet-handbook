# Frequently asked questions

## Which projects are a good fit?

Consider who will act on the decision you make this round. If a deliverable comes back for revision and someone else takes it over, they need to know which criterion it missed and who can change that criterion. A project like that benefits from a record of responsibilities, authority and reasons. For a one-off task you can accept yourself, with nobody else taking over, use the tools you already know.

## How do existing workflows and subagents fit in?

Keep running the steps and checks that already work. Give parallel tasks to subagents as usual. In each brief, name the file to deliver, who receives it and what would send it back. If a workflow flags two results that disagree, for example, the role responsible for acceptance can check the source files and record the reason for its decision. See [Chapter 1](01-what-is-an-ai-fleet.md) and [Chapter 2](02-write-and-review.md).

## What evidence is there that the organization improves its own practices?

The handbook records three changes our fleet made. Each account describes the problem and the responsibility or rule that changed.

- [Chapter 1 explains why the fleet added a duty role.](01-what-is-an-ai-fleet.md#change-duty-role)
- [Chapter 4 shows which decisions a role could make and when they went back to the human.](04-decisions.md#change-conditional-authority)
- [Chapter 5 records how two members’ objections changed the wording on who could exercise judgment.](05-values.md#change-decision-rights)

## How is this different from an agent swarm?

In some swarms, a lead model splits up a task on the spot and sends subagents to work in parallel. What carries over varies by system. In a LangGraph example, the model revises its system prompt in response to feedback and saves it for later sessions. In Paperclip, a manager agent can request a new role, and project settings determine whether the board reviews the request. [LangGraph example](https://docs.langchain.com/oss/python/concepts/memory) · [Paperclip hiring approvals](https://docs.paperclip.ing/how-to/handle-board-approvals-for-hires/)

Our AI fleet can assemble a swarm for a single task. When that task ends, its standing roles keep their responsibilities and decision rights, even if a different model takes over. For example, every push to our repository used to wait for the human. After several pushes, the human gave the role responsible for that repository authority to approve them while it stayed private. Once the repository is public, the human approves pushes again. [The delegation recorded in Chapter 4](04-decisions.md#change-conditional-authority)

[Chapter 1 records why the project manager proposed a duty role to take over job monitoring and status checks.](01-what-is-an-ai-fleet.md#change-duty-role)

## Does this count as recursive self-improvement (RSI)?

Here the organization revises its own practices. A problem in one round can prompt members to propose a change to roles or rules. The next round can then use the revised arrangement. The models do not modify themselves in this process.

Peers review each proposed change, then a model from another provider checks it. Record the change, the reviews and the reason for the decision so the next member can check them.

The project’s [approval table](../../skills/fleet-setup/templates/en/approvals.md) says who decides each kind of change. A team can delegate a class of changes to a role and specify when that authority applies and when to hand the decision back. The human sets direction, handles external commitments, spending and deletion, and can take part in any judgment.

The three accounts above show what changed. We have no before-and-after measurements of how often the same errors occurred on comparable tasks judged by the same criteria.

## Can I start with just one model provider?

Yes. Pick a decision in your project, write the task brief, deliver the original files and leave a handoff. A fresh session can help spot an oversight. Keep cross-provider review marked as pending until you have connected and tested a second provider. Then use the providers listed in the roster to choose an independent reviewer. See [Chapter 2](02-write-and-review.md).

## Can I trust work after another provider reviews it?

Check what was reviewed. The reviewer reads the original material, task brief and output, then checks against the acceptance criteria. The project manager addresses findings and disagreements. Authors do not accept their own work, including project managers who helped write it. See [Chapter 2](02-write-and-review.md).

## Can several people use this together?

You can divide work around a shared project. The roster records roles and reporting relationships; the approval table records who decides each kind of matter. When different people hold responsibility for direction, authorization or acceptance, make those scopes explicit.

For simultaneous work, use distinct task briefs and output files, and avoid editing the same file at once. Preserve existing root project-card content, and append to handoffs and decisions. Before stopping, record who resumes and when. See [Chapter 3](03-memory.md) and [Chapter 4](04-decisions.md).

## What should a new session read first?

Start with the project card and the latest handoff for your role and task. Open the deliverable to verify its state. For the reason behind a decision, look up the relevant entry in the decision log. See [Chapter 3](03-memory.md).

## Can we adopt the six values from the handbook?

Use them as a reference. Take a real disagreement in your team and ask members which principle changed the choice and what objections they raised. Record the decision and its reasons. See [Chapter 5](05-values.md).

## How do I install the skills?

Follow the [installation guide](../../install/README.md) for the project you want to work on. If the project already has a card and a roster, check them first and keep the assignments that are in place.

## How should I read my self-check result?

Open the [nine-question self-check](../../levels/index.html) in your browser and answer from recent work. Look for a gap in how you divide, review or hand over work and address it next round. The level describes your practices. To tell whether an error recurs less often, check the actual deliverables.

## Once the skills are installed, what should I do first?

Start with a decision in your project. Tell the project manager, “This week we need to decide [a specific choice]. The source material is in [location]. Please write down who will deliver the original files, who will check them, what would send the work back and which decision is mine.”

Return the deliverable, the acceptance decision and any open questions. The next member should be able to open the work, trace the reason for the decision and say which step comes next. To see how an assignment grew into a standing role, read [the duty-role account in Chapter 1](01-what-is-an-ai-fleet.md#change-duty-role).
