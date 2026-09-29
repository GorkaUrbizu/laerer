#!/usr/bin/env python3
"""Lærer - a terminal quiz for learning Norwegian words."""

import argparse
import json
import os
import random
import re
import sys
from pathlib import Path

DEFAULT_WORDS = Path(__file__).resolve().parent / "norwegian_words.jsonl"
DEFAULT_SENTENCES = Path(__file__).resolve().parent / "sentences.jsonl"
NUM_OPTIONS = 4
LABELS = "ABCD"

# Word types asked more often by default (use --uniform to disable).
FOCUS_TYPES = {"Substantiver", "Verb", "Adjektiv"}
FOCUS_WEIGHT = 2

TYPE_NAMES = {
    "Substantiver": "noun",
    "Verb": "verb",
    "Adjektiv": "adjective",
    "Adverb": "adverb",
    "Preposisjoner": "preposition",
    "Konjuksjoner": "conjunction",
    "Pronomener": "pronoun",
    "Spørreord": "question word",
    "Andre ord": "other",
}


# ---------------------------------------------------------------- colors ---

class Style:
    enabled = True

    CODES = {
        "reset": "0", "bold": "1", "dim": "2", "italic": "3", "underline": "4",
        "red": "31", "green": "32", "yellow": "33", "blue": "34",
        "magenta": "35", "cyan": "36", "white": "37", "grey": "90",
        "bright_red": "91", "bright_green": "92", "bright_yellow": "93",
        "bright_blue": "94", "bright_magenta": "95", "bright_cyan": "96",
    }

    @classmethod
    def paint(cls, text, *styles):
        if not cls.enabled or not styles:
            return str(text)
        codes = ";".join(cls.CODES[s] for s in styles)
        return f"\033[{codes}m{text}\033[0m"


def c(text, *styles):
    return Style.paint(text, *styles)


def rule(width=60, color="grey"):
    return c("─" * width, color)


# ------------------------------------------------------------------ data ---

def load_words(path):
    words = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                norsk = entry["norsk"].strip()
                engelsk = entry["engelsk"].strip()
                wtype = entry["type"].strip()
                # Shown before the word: "et år" teaches gender, "å like"
                # marks infinitives (also "bli med", filed under "Andre ord").
                marker = entry.get("artikkel", "").strip()
                is_verb = wtype == "Verb" or engelsk.startswith("to ")
                if not marker and is_verb and not norsk.startswith("det "):
                    marker = "å"
                words.append({
                    "norsk": norsk,
                    "markør": marker,
                    "vis": f"{marker} {norsk}" if marker else norsk,
                    "engelsk": engelsk,
                    "type": wtype,
                })
            except (json.JSONDecodeError, KeyError) as e:
                print(c(f"Skipping line {lineno}: {e}", "yellow"), file=sys.stderr)
    return words


def group_by_type(words):
    groups = {}
    for w in words:
        groups.setdefault(w["type"], []).append(w)
    return groups


def meanings(english):
    """Split 'to hear, to listen; to obey' into {'hear', 'listen', 'obey'}.

    Notes in parentheses are ignored, so 'you (plural)' overlaps with 'you'.
    """
    parts = english.replace(";", ",").replace("/", ",").split(",")
    result = set()
    for p in parts:
        p = re.sub(r"\([^)]*\)", "", p)
        p = " ".join(p.split()).lower()
        if p.startswith("to "):
            p = p[3:]
        if p:
            result.add(p)
    return result


def build_question(word, groups, reverse):
    """Return (options, correct_index): word entries, same-type distractors."""
    answer = "vis" if reverse else "engelsk"

    # Distractors: same type, no shared meaning with the correct word
    # (so "correct" is never offered next to "right, correct"), no duplicates.
    target = meanings(word["engelsk"])
    seen = {word[answer].lower()}
    candidates = []
    for w in groups[word["type"]]:
        key = w[answer].lower()
        if key in seen or w["norsk"].lower() == word["norsk"].lower():
            continue
        if meanings(w["engelsk"]) & target:
            continue
        seen.add(key)
        candidates.append(w)

    distractors = random.sample(candidates, min(NUM_OPTIONS - 1, len(candidates)))
    options = distractors + [word]
    random.shuffle(options)
    return options, options.index(word)


def norsk_text(word, *styles):
    """Norwegian word with its article / infinitive marker in plain white."""
    marker = word["markør"]
    prefix = c(marker, "white") + " " if marker else ""
    return prefix + c(word["norsk"], *styles)


# ------------------------------------------------------------------- game --

def banner(reverse, total):
    direction = "English  ->  Norwegian" if reverse else "Norwegian  ->  English"
    print()
    print(rule(60, "blue"))
    print("  " + c("L Æ R E R", "bold", "bright_cyan")
          + c("   ·   learn Norwegian words", "grey"))
    print("  " + c(direction, "cyan") + c(f"   ·   {total} questions", "grey"))
    print(rule(60, "blue"))
    print(c("  Answer with A-D (or 1-4). Type q to quit.", "grey"))


def ask_choice():
    while True:
        try:
            raw = input(c("  Your answer: ", "bold", "white")).strip().upper()
        except EOFError:
            print()
            return None
        if raw in ("Q", "QUIT", "EXIT"):
            return None
        if len(raw) == 1 and raw in LABELS[:NUM_OPTIONS]:
            return LABELS.index(raw)
        if raw.isdigit() and 1 <= int(raw) <= NUM_OPTIONS:
            return int(raw) - 1
        print(c(f"  Please enter A-{LABELS[NUM_OPTIONS - 1]} "
                f"or 1-{NUM_OPTIONS}.", "yellow"))


def weighted_sample(words, k, uniform):
    """Pick k distinct words; focus types are FOCUS_WEIGHT times as likely."""
    if uniform:
        return random.sample(words, k)
    # Efraimidis-Spirakis: weighted sampling without replacement.
    def key(w):
        weight = FOCUS_WEIGHT if w["type"] in FOCUS_TYPES else 1
        return random.random() ** (1 / weight)
    return sorted(words, key=key, reverse=True)[:k]


def load_sentences(path):
    """Map (norsk, type) -> example sentence entry. Missing file is fine."""
    sentences = {}
    if not path.exists():
        return sentences
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                s = json.loads(line)
                sentences[(s["norsk"], s["type"])] = s
    return sentences


def highlight(sentence, base="white"):
    """Render 'Jeg [liker] kaffe.' with the bracketed word highlighted."""
    before, rest = sentence.split("[", 1)
    target, after = rest.split("]", 1)
    return (c(before, base) + c(target, "bold", "underline", "bright_yellow")
            + c(after, base))


def play(words, num_questions, reverse, uniform=False, sentences=None):
    sentences = sentences or {}
    groups = group_by_type(words)
    # Only use words whose type can provide enough distractors.
    playable = [w for w in words if len(groups[w["type"]]) >= NUM_OPTIONS]
    num_questions = min(num_questions, len(playable))
    selection = weighted_sample(playable, num_questions, uniform)

    banner(reverse, num_questions)
    results = []

    def option_text(w, *styles):
        return norsk_text(w, *styles) if reverse else c(w["engelsk"], *styles)

    for i, word in enumerate(selection, 1):
        options, correct_idx = build_question(word, groups, reverse)
        wtype = TYPE_NAMES.get(word["type"], word["type"])
        example = sentences.get((word["norsk"], word["type"]))

        print()
        print(c(f"  Question {i}/{num_questions}", "bold", "blue")
              + c(f"  [{wtype}]", "magenta"))
        print()
        if reverse:
            # The Norwegian sentence would give the answer away.
            line = "    " + c(word["engelsk"], "bold", "bright_yellow")
        else:
            line = "    " + norsk_text(word, "bold", "bright_yellow")
            if example:
                line += c("   ·   ", "grey") + highlight(example["setning"])
        print(line)
        print()
        for j, opt in enumerate(options):
            print(f"    {c(LABELS[j], 'bold', 'cyan')}{c(')', 'grey')} "
                  f"{option_text(opt)}")
        print()

        choice = ask_choice()
        if choice is None:
            print(c("\n  Quiz stopped early.", "yellow"))
            break

        ok = choice == correct_idx
        results.append({
            "word": word,
            "given": options[choice],
            "reverse": reverse,
            "ok": ok,
        })

        def labelled(idx, *styles):
            return (c(f"{LABELS[idx]}) ", *styles)
                    + option_text(options[idx], *styles))

        if ok:
            print("  " + c("CORRECT", "bold", "bright_green")
                  + c("  ·  ", "grey") + labelled(correct_idx, "green"))
        else:
            print("  " + c("WRONG", "bold", "bright_red")
                  + c("  ·  you chose ", "grey") + labelled(choice, "red"))
            print("  " + c("Correct answer: ", "grey")
                  + labelled(correct_idx, "bold", "green"))
        print("  " + norsk_text(word, "bright_cyan")
              + c(" = ", "grey") + c(word["engelsk"], "white"))
        if example and not ok:
            if reverse:
                print("  " + highlight(example["setning"]))
            print("  " + c(example["oversettelse"], "italic", "grey"))
        print(rule())

    show_results(results)


def show_results(results):
    total = len(results)
    print()
    print(rule(60, "blue"))
    print("  " + c("RESULTS", "bold", "bright_cyan"))
    print(rule(60, "blue"))

    if total == 0:
        print(c("  No questions answered.", "grey"))
        print()
        return

    score = sum(r["ok"] for r in results)
    pct = 100 * score / total
    if pct >= 80:
        color, msg = "bright_green", "Utmerket! Excellent work."
    elif pct >= 50:
        color, msg = "bright_yellow", "Bra! Keep practising."
    else:
        color, msg = "bright_red", "Øvelse gjør mester. Practice makes perfect."

    bar_width = 30
    filled = round(bar_width * score / total)
    bar = c("█" * filled, color) + c("░" * (bar_width - filled), "grey")

    print()
    print(f"  Score: {c(f'{score}/{total}', 'bold', color)}"
          f"  {c(f'({pct:.0f}%)', color)}")
    print(f"  {bar}")
    print(f"  {c(msg, 'italic', color)}")
    print()

    width = max(len(r["word"]["vis"]) for r in results) + 2
    for i, r in enumerate(results, 1):
        mark = c("+", "bold", "green") if r["ok"] else c("x", "bold", "red")
        pad = " " * (width - len(r["word"]["vis"]))
        norsk = norsk_text(r["word"], "bright_cyan") + pad
        line = f"  {c(f'{i:>2}.', 'grey')} {mark} {norsk}{r['word']['engelsk']}"
        if not r["ok"]:
            given = r["given"]
            given_text = (norsk_text(given, "red") if r["reverse"]
                          else c(given["engelsk"], "red"))
            line += c("   (you: ", "red") + given_text + c(")", "red")
        print(line)

    mistakes = [r for r in results if not r["ok"]]
    if mistakes:
        print()
        print(c(f"  Words to review: {len(mistakes)}", "yellow"))
    print(rule(60, "blue"))
    print()


# ------------------------------------------------------------------- main --

def main():
    parser = argparse.ArgumentParser(
        description="Terminal quiz for learning Norwegian words.")
    parser.add_argument("-n", "--questions", type=int, default=10,
                        help="number of questions (default: 10)")
    parser.add_argument("-r", "--reverse", action="store_true",
                        help="show English, answer in Norwegian")
    parser.add_argument("-u", "--uniform", action="store_true",
                        help="pick every word with equal chance (by default "
                             "nouns, verbs and adjectives are twice as likely)")
    parser.add_argument("-t", "--type", action="append", metavar="TYPE",
                        help="only ask words of this type, e.g. verb, noun, "
                             "adjective (can be repeated)")
    parser.add_argument("-f", "--file", type=Path, default=DEFAULT_WORDS,
                        help="path to the word list (JSONL)")
    parser.add_argument("--no-sentences", action="store_true",
                        help="show the bare word instead of an example sentence")
    parser.add_argument("--no-color", action="store_true",
                        help="disable colored output")
    parser.add_argument("--list-types", action="store_true",
                        help="list available word types and exit")
    args = parser.parse_args()

    Style.enabled = (not args.no_color and sys.stdout.isatty()
                     and "NO_COLOR" not in os.environ)

    if args.questions < 1:
        parser.error("--questions must be at least 1")

    words = load_words(args.file)
    groups = group_by_type(words)

    if args.list_types:
        for t, ws in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            print(f"  {c(TYPE_NAMES.get(t, t).ljust(14), 'cyan')}"
                  f"{c(t.ljust(15), 'grey')}{len(ws):>4} words")
        return

    if args.type:
        wanted = {t.lower() for t in args.type}
        words = [w for w in words
                 if w["type"].lower() in wanted
                 or TYPE_NAMES.get(w["type"], "").lower() in wanted]
        if not words:
            parser.error("no words match that type (see --list-types)")

    try:
        sentences = {} if args.no_sentences else load_sentences(DEFAULT_SENTENCES)
        play(words, args.questions, args.reverse, args.uniform, sentences)
    except KeyboardInterrupt:
        print(c("\n\n  Ha det! Goodbye.\n", "yellow"))


if __name__ == "__main__":
    main()
