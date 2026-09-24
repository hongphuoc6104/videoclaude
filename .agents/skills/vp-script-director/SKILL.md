---
name: vp-script-director
description: Critique a complete Vietnamese horror narration draft against six story criteria before content submission; use for horror_story briefs with script_director enabled.
---

# Horror script director

The writer owns the draft. Score the entire spoken Vietnamese story after structural validation. Preserve quoted Vietnamese evidence exactly. This critique is internal; it never approves content or changes its words, outline, coverage, claims, images, or anchors. A failed draft returns to the writer for a complete regeneration: finalize narration first, then place fresh quotes and anchors. The existing content review gate still applies.

Use `horror/narration-style.md` and the brief's mood and point of view. Give each criterion an integer score from 0 to 2, at least one scene-specific quote as evidence, and concrete notes:

| Criterion | 0 | 1 | 2 |
| --- | --- | --- | --- |
| `dread_escalation` | No rising omen, or a monster is fully exposed at once | Omens rise unevenly or false relief is missing | Each omen is closer, more personal, or harder to explain; one midstory false relief |
| `pacing_rhythm` | Flat, uniformly long sentences around scares | Slows before a scare, but the scare line stays buried | Two or three short ordinary sentences precede a separate 3–8 word scare line |
| `climax_payoff` | Twist is unrelated to planted detail | The detail returns weakly or too early | An ordinary early detail returns and changes meaning at the twist |
| `oral_storytelling_voice` | Literary prose or many tangled clauses | Mostly speakable with a few bookish lines | Natural spoken Vietnamese, mostly 6–20 words per sentence, at most two ellipses per scene |
| `cliche_budget` | A listed cliché repeats at least twice | No listed phrase repeats, but clichés crowd the narration | At or under the per-phrase budget in the style guide, with specific physical detail instead |
| `hook_per_scene` | Two or more nonfinal scenes end without a hook | One nonfinal scene lacks a hook | Every nonfinal scene ends on a question, unexplained detail, or interrupted action |

The code computes pass: every criterion at least 1 and total at least 10 of 12. Supply `revision_requests` for weak spots with criterion, affected scene IDs, and a specific rewrite instruction. The adapter assigns each request an `SD…` ID, sends it to the writer, and requires a matching `revision_response` with the scene IDs. An unresolved request reaches `open_questions` in review mode and stops auto mode. Never claim the draft passes in prose. The adapter allows at most two complete writer rewrites; in auto mode exhaustion stops with `needs_attention`, while review mode shows the findings in `open_questions` for the human review. Every round's scored evidence and writer response are saved under the job's `agent-attempts` directory.
