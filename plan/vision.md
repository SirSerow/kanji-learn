This application in intended to be used in preparation to the JLPT exam, specifically, it aims to help increasing the kanji learning speed.

## Format
- The application is build in a from of web app.  

## User experience
- Each user has his own account in which he can track his learning progress.
- User should be able to check the learning paste himself.
- The application must give user an opportunity to learn or prepare for specific level (for example N3)
- The user should be able to track his progress over the different JLPT levels
## Methods
| Layer               | What to implement                                                       |
| ------------------- | ----------------------------------------------------------------------- |
| **Core engine**     | FSRS or SM-2 spaced repetition                                          |
| **Teaching method** | Radicals → mnemonic→ reading → vocabulary                               |
| **Card design**     | One kanji per card; meaning, reading, memonics and context              |
| **Ordering**        | Frequency rank or JLPT level; radicals before the kanji that use them   |
| **Daily pace**      | 5–15 new kanji/day; reviews always come first                           |
| **Input type**      | Active recall (typed or selected), not passive multiple choice          |
| **Progress**        | Multi-stage mastery levels visible to the user                          |
| **Illustration**    | Image generation to help user memorize kanji based on his own mnemonics |

### Types of Tests to Include

**1. Recognition Quiz (multiple choice)** Show a kanji, pick the correct meaning or reading from 4 options. Fast, low-friction, good for measuring breadth across many kanji quickly. The wrong options (distractors) should be semantically close — not random — so the test actually challenges understanding rather than elimination. For example, testing 日 (sun/day), the distractors should be 月 (moon), 火 (fire), 明 (bright) — not 犬 (dog) and 食 (eat).

**2. Recall Quiz (typed answer)** Show a kanji, type the reading or meaning. Much harder than multiple choice because there's no scaffolding. This is the format most correlated with real-world reading ability. Research consistently shows typed recall produces stronger long-term retention than recognition.

**3. Timed Speed Round** Flash kanji one by one, 3–5 seconds each, tap the correct answer. Tests automaticity — whether you _know_ it or have to _think_ about it. A kanji you hesitate on but answer correctly is actually weaker than SRS signals suggest.


