# Horror narration style (Vietnamese spoken storytelling)

Applies to briefs with `video_type: horror_story`. It adds to the general narration guide. The hard rules there still win: never drop or merge required points, and write and freeze the narration before placing coverage quotes and beat anchors.

The narration is heard, not read, in one deep male Vietnamese TTS voice at a slow pace. Write for the ear.

## Voice

- A close, low storyteller at night, like someone telling a story by a single lamp. Calm, never shouting. Let the facts frighten, not adjectives.
- The channel host (the mascot narrator) speaks only in the first and the last scene. The host may address the listener as "bạn". Inside the story nobody addresses the listener.
- Follow the point of view stated in the brief (`Ngôi kể`):
  - Third person: stay close to one protagonist. Tell only what that person sees, hears and thinks.
  - First person: in scene 1 the host introduces the teller and hands over. From scene 2 to the second-last scene the protagonist says "tôi". The host returns in the last scene.

## How fear is built

- Build fear from a small wrong detail, not from a monster on display. Examples: a sound in the wrong place, an object that moved, a count that is off by one, a reflection a moment late.
- Every scene carries at least one concrete sensory detail beyond sight: sound, smell, temperature or touch. Describe sounds in words, with their rhythm: "tiếng gõ ba nhịp, dừng, rồi thêm một nhịp".
- Show the edge, not the centre. Do not describe the entity in full, even at the climax. A hand, a shape behind a curtain or a voice that is almost right is enough.
- Escalation rule: each omen is closer, more personal or harder to explain than the one before. The protagonist first explains it away, then doubts, then cannot deny it.
- Include one false relief in the middle: a moment when everything seems explained.
- Plant, then pay off. At least one ordinary detail from the setup returns in the climax or the twist and changes its meaning.
- Before a scare, slow down with two or three short, ordinary sentences. The scare line itself is short. The next sentence starts after a full stop, never in the same sentence.
- End every scene except the last on a small hook: an unanswered question, an unexplained detail or an action cut off.

## Sentences and rhythm (TTS-safe)

- Most sentences are 6–20 words. Vary the length. Scare lines are 3–8 words.
- Use full stops and commas for pauses. Use "…" at most twice per scene. No exclamation marks outside dialogue. No all-caps words. No stretched letters ("aaaa").
- Dialogue: at most three short lines per scene, in quotation marks, with the speaker named before the line ("Bà cụ nói nhỏ: “…”"). One voice reads everything, so the listener must always know who speaks.
- Write numbers and times as words ("hai giờ sáng").
- Scene length follows the word target given in the call, which comes from the video length. It overrides the 256-character note in the general guide. Long scenes are fine because the voice is synthesized sentence by sentence, so make every sentence stand on its own.

## Vietnamese texture

- Use everyday words with concrete objects of Vietnamese life (quạt trần, mái tôn, chum nước, đèn dầu, bàn thờ, xe máy, chợ phiên). Places stay fictional and generic.
- Beliefs are shown with respect. Altars, incense and ancestors can be part of the setting. They are never mocked, never explained as rituals and never turned into instructions.
- Limit clichés to at most one of each per video: "bỗng nhiên", "một luồng khí lạnh chạy dọc sống lưng", "tim đập thình thịch", "rợn tóc gáy", "không gian như ngừng lại". Replace them with a specific physical detail.
- No meta-comments inside the story ("thật đáng sợ phải không"). Save them for the host scenes.

## Structure (share of scenes)

| Part | Share | What happens |
|---|---|---|
| Opening (host) | scene 1 | First sentence is a concrete strange image or question, never a greeting. Then say clearly the story is fiction. Then hand over. |
| Setup | ~20% | Ordinary life. The protagonist wants something (money, rest, family). The place. A first small oddity by the end. |
| Escalation | ~45% | The seed's omens, each stronger. One false relief. |
| Climax and twist | ~20% | Short, direct scenes. The twist reframes a planted detail. |
| Aftermath | ~10% | Consequences and one lingering detail. No over-explaining. |
| Closing (host) | last scene | Close the story, repeat that it is fiction, invite comments. Never dare the listener to try anything. |

## Mood (`Không khí (mood)` in the brief)

- `slow_burn`: long, careful everyday detail. Omens start small and far apart, then come faster. Only one real jolt, at the climax. A quiet ending.
- `psychological`: the protagonist doubts their own mind. Alternate normal moments with slightly wrong ones. The twist changes how the whole story reads. The ending stays open.
- `folk`: tell it like an old village tale, with warnings, village customs, weather, water and trees. The tone is sad more than shocking. The climax is quiet but heavy.
- `tense`: get into the story fast. Every scene has a turn. There are two moments where escape seems possible, and short sentences under pressure. The climax lasts longer than in the other moods.

## Sound

- A quiet bed plays under the whole video; do not describe music in the narration.
- A scene may carry one `sfx` cue from the listed CC0 ids, only where the narration itself names that sound ("ba tiếng gõ", "tiếng cửa kẽo kẹt"). Anchor it on those words. Most scenes have none; silence is part of the fear.

## Images for horror scenes

- The host appears only in images of the first and last scene. List the host in those scenes' `character_ids`, and nowhere else.
- Story scenes use the story's own characters, declared in `characters` with a full `appearance` and `outfit` (face, age, hair, build, clothes). Those two fields are the only thing that keeps a character the same across images, so write them precisely.
- Compose with darkness, one warm light source, silhouettes, partial views and empty space. Show the threat partly: a shadow, a hand, an outline. Never show gore, blood or a corpse.
- `visible_text` is almost always empty. Do not draw signs with real place names.
