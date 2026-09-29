# Lærer

A colorful terminal quiz for learning Norwegian words.

A multiple-choice quiz over the 300 most frequently used Norwegian words (from
the Norwegian Academy list). Each question shows the word, with its article for
nouns so you learn the gender (`et år`, `ei jente`) and the infinitive
marker for verbs (`å like`), shown in white, next to a short,
simple example sentence (A1-A2 level) with the word highlighted, and four
possible English translations.
The three wrong options (distractors) are always taken from the same word type
as the correct answer (verb, adjective, noun, ...), so you can't guess from
the grammar alone. After every question the correct answer is shown; if you got
it wrong, the English translation of the sentence is shown too. At the end you
get a score summary with the words you should review.

## Requirements

- Python 3.8+ (standard library only, nothing to install)
- A terminal with ANSI color support

## Usage

```bash
python3 laerer.py                 # 10 random questions, Norwegian -> English
python3 laerer.py -n 20           # 20 questions
python3 laerer.py -r              # reverse: English -> Norwegian
python3 laerer.py -u              # every word equally likely
python3 laerer.py -t verb         # only verbs
python3 laerer.py -t noun -t adjective
python3 laerer.py --list-types    # show available word types
python3 laerer.py --no-color      # plain output
```

Answer with `A`-`D` (or `1`-`4`). Type `q` to stop early; the results for the
questions answered so far are still shown.

### Options

| Option             | Description                                        |
| ------------------ | -------------------------------------------------- |
| `-n, --questions`  | Number of questions (default: 10)                  |
| `-r, --reverse`    | Show English, answer in Norwegian                  |
| `-u, --uniform`    | Pick every word with equal chance (see below)      |
| `-t, --type`       | Only use this word type (repeatable)               |
| `-f, --file`       | Use a different word list (JSONL)                  |
| `--no-sentences`   | Show only the word, without the example sentence   |
| `--list-types`     | List word types and counts, then exit              |
| `--no-color`       | Disable colors (also honors the `NO_COLOR` env var) |

Word types can be given in English (`verb`, `noun`, `adjective`, `adverb`,
`preposition`, `conjunction`, `pronoun`, `question word`, `other`) or with the
Norwegian names used in the data file (`Substantiver`, `Adjektiv`, ...).

### Word selection

Questions are picked at random, without repeats. By default, nouns, verbs and
adjectives are **twice as likely** to be picked as other words, so they make up
about 6-7 of every 10 questions instead of about 5. With `--uniform` every word
has the same chance, so the mix of types follows the word list (adverbs are
the most common there).

The focus types and weight are set by `FOCUS_TYPES` and `FOCUS_WEIGHT` at the
top of `laerer.py`.

## Word list format

`norwegian_words.jsonl` has one JSON object per line:

```json
{"norsk": "sterk", "engelsk": "strong", "type": "Adjektiv"}
{"norsk": "år", "artikkel": "et", "engelsk": "year", "type": "Substantiver"}
```

Nouns have an optional `artikkel` field (`en`, `et` or `ei`), shown in the
game as `et år`. Every noun that can be feminine (mor, kvinne, jente, hånd,
stund, dør, krone, side, sak, tid, regjering) is marked `ei`, and the
sentences use the feminine definite form (`Mora mi`, `hånda`, `Tida`) so the
gender is visible. In Bokmål these can also take `en` (`moren min`), but
masculine nouns can never take `ei`, so learning the feminine ones as feminine
and defaulting to `en` when unsure is the safe strategy. Other articles come
from the PDF; the few nouns the
PDF lists without one (tid, krone, menneske, verden, prosent, politi, meter)
use the standard Bokmål gender. Plurals and non-count words (mennesker,
penger, alle, alt) have no article.

The same field holds the article in fixed expressions: `de andre`,
`de fleste`, `en/et slags`. An optional `tillegg` field adds a word after,
e.g. `enda mer`. Both are shown in white; verbs get `å` automatically.

`sentences.jsonl` has one example sentence per word, matched on `norsk` +
`type`. The word to highlight is wrapped in `[brackets]`; nouns may appear in
definite or plural form, adjectives inflected, and verbs in the present tense:

```json
{"norsk": "like", "type": "Verb", "setning": "Jeg [liker] kaffe.", "oversettelse": "I like coffee."}
```

In reverse mode (`-r`) the English word is shown instead, since the Norwegian
sentence would give the answer away; the sentence is shown after a wrong
answer. Words without a sentence are shown on their own.

Distractors never share a meaning with the correct answer (for example,
`correct` is never offered as a wrong option for `right, correct`).

## TODO

- [ ] A second game based on `norwegian_verbs.jsonl` to practise verb
      conjugation (infinitiv, presens, preteritum, perfektum), e.g. show
      `å begynne` and ask for its preteritum form.
