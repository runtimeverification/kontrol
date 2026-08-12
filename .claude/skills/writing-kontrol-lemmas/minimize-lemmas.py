#!/usr/bin/env python3
"""Progressively disable lemmas and report which are load-bearing.

For each rule name given on the command line:

  1. Snapshot the current lemmas file to a checkpoint.
  2. Comment out the rule block (matches ``rule [NAME]: … [simplification,
     …]`` at any indent, as long as it starts at the beginning of a line).
  3. Run the user-supplied spec runner with the spec stem as its single
     argument.
  4. If the runner exits zero and ``PROOF PASSED`` appears exactly
     ``--expected-passes`` times, mark the rule REMOVABLE and keep it
     disabled. Otherwise (non-zero exit, or count mismatch) mark it
     NECESSARY and restore from the checkpoint. A non-zero runner exit
     is always conservative: stale/cached output that happens to hit
     the expected count can't outvote a crash signal. Runner stdout and
     stderr are surfaced on the non-zero path for debugging.

A TSV log is written to ``--results-file``.

Order matters: a rule that is removable on its own may become necessary
after an earlier rule is dropped. Put "load-bearing suspects" first if
you want them confirmed against the full set.

The lemmas file must already hold the full (pre-minimization) rule set
when this script starts. Pass ``--pristine PATH`` to have the script
restore from a pre-frozen copy before the first iteration; without it
the file is taken as-is.

Example:
    ./minimize-lemmas.py \\
        --project-root /home/me/code/my-project \\
        --lemmas-file test/kontrol/lemmas.k \\
        --spec-runner scripts/kontrol-lemma-test.sh \\
        --spec-stem my-spec \\
        --expected-passes 4 \\
        rule-a rule-b rule-c

Depends only on the Python standard library.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Final, NamedTuple


PROOF_PASSED_MARKER: Final[str] = "PROOF PASSED"

# Match a *named* simplification rule at any indent. `^[ \t]*` anchors to
# line start (MULTILINE) and captures whatever leading whitespace the
# project uses; KEVM/Kontrol convention is 4-space, but sub-modules or
# alternative styles can shift that, so we don't hard-code a width.
#
# The tempered dot `(?!^[ \t]*rule[ \t]).` stops the lazy run from
# crossing into the next rule header — *named or unnamed* — so a non-
# simplification rule cannot absorb a later rule's `[simplification ...]`
# and comment out two blocks at once. Unnamed simplification rules
# (`rule LHS => RHS [simplification]` with no `[label]:`) are legal K
# syntax; this script can't probe them because it dispatches on rule
# names from the CLI, but the boundary still has to recognize them so
# they don't get silently swallowed into a neighbor's match.
RULE_BLOCK_RE: Final[re.Pattern[str]] = re.compile(
    r"^[ \t]*rule \[(?P<name>[^\]]+)\]:"
    r"(?:(?!^[ \t]*rule[ \t]).)*?"
    r"\[simplification[^\]]*\]",
    re.DOTALL | re.MULTILINE,
)


class DisableResult(NamedTuple):
    """Outcome of trying to comment out a single rule block."""

    found: bool
    detail: str


class RuleVerdict(NamedTuple):
    """Row emitted to the results TSV for each probed rule."""

    rule: str
    result: str  # "removable" | "necessary" | "not-found"


def disable_rule(rule: str, lemmas_file: Path) -> DisableResult:
    """Comment out a named simplification rule block, writing in place."""
    src = lemmas_file.read_text()
    for match in RULE_BLOCK_RE.finditer(src):
        if match.group("name") != rule:
            continue
        block = match.group(0)
        commented = "\n".join("//" + line for line in block.split("\n"))
        lemmas_file.write_text(src[: match.start()] + commented + src[match.end():])
        return DisableResult(
            found=True,
            detail=f"disabled [{rule}] in {lemmas_file}",
        )
    return DisableResult(
        found=False,
        detail=f"no rule [{rule}] matched in {lemmas_file}",
    )


def run_spec(spec_runner: Path, spec_stem: str, cwd: Path) -> int:
    """Run ``<spec_runner> <spec_stem>`` from ``cwd``; return PROOF PASSED count.

    Raises ``subprocess.CalledProcessError`` if the runner exits
    non-zero; the caller folds that into NECESSARY (a crashed runner
    can't certify a rule as removable, even if PROOF PASSED happens to
    appear ``--expected-passes`` times in stale or partial output).
    """
    result = subprocess.run(
        [str(spec_runner), spec_stem],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    matching_lines = list(
        filter(lambda line: PROOF_PASSED_MARKER in line, combined.splitlines())
    )
    return len(matching_lines)


def minimize(
    *,
    project_root: Path,
    lemmas_file: Path,
    spec_runner: Path,
    spec_stem: str,
    expected_passes: int,
    rules: list[str],
    pristine: Path | None,
    results_file: Path,
    checkpoint: Path,
) -> int:
    if not project_root.is_dir():
        print(
            f"error: --project-root is not a directory: {project_root}",
            file=sys.stderr,
        )
        return 1

    lemmas_abs = (project_root / lemmas_file).resolve()
    if not lemmas_abs.is_file():
        print(f"error: lemmas file not found: {lemmas_abs}", file=sys.stderr)
        return 1

    if pristine is not None:
        if not pristine.is_file():
            print(
                f"error: --pristine file not found: {pristine}\n"
                f"       create it once before the first run, e.g.:\n"
                f"           cp {lemmas_abs} {pristine}",
                file=sys.stderr,
            )
            return 1
        shutil.copy2(pristine, lemmas_abs)
        print(f"restored {lemmas_abs} from pristine {pristine}")

    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text("rule\tresult\n")

    def append_verdict(verdict: RuleVerdict) -> None:
        with results_file.open("a") as f:
            f.write(f"{verdict.rule}\t{verdict.result}\n")

    for rule in rules:
        shutil.copy2(lemmas_abs, checkpoint)

        disable = disable_rule(rule, lemmas_abs)
        if not disable.found:
            print(f">>> {rule} NOT FOUND — skipping ({disable.detail})")
            append_verdict(RuleVerdict(rule=rule, result="not-found"))
            shutil.copy2(checkpoint, lemmas_abs)
            continue

        print(f">>> testing without [{rule}]...")
        try:
            passes = run_spec(spec_runner, spec_stem, project_root)
        except FileNotFoundError as e:
            print(f"error: spec runner not executable: {e}", file=sys.stderr)
            shutil.copy2(checkpoint, lemmas_abs)
            return 1
        except KeyboardInterrupt:
            print(
                f"\ninterrupted during [{rule}] — restoring "
                f"{lemmas_abs} from checkpoint",
                file=sys.stderr,
            )
            shutil.copy2(checkpoint, lemmas_abs)
            raise

        if passes == expected_passes:
            print(f">>> {rule} REMOVABLE")
            append_verdict(RuleVerdict(rule=rule, result="removable"))
        else:
            print(
                f">>> {rule} NECESSARY "
                f"({passes} / {expected_passes} passes)"
            )
            append_verdict(RuleVerdict(rule=rule, result="necessary"))
            shutil.copy2(checkpoint, lemmas_abs)

    print()
    print("=== Summary ===")
    sys.stdout.write(results_file.read_text())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Minimize a K lemmas file by progressively disabling rules "
            "and rerunning a spec."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        required=True,
        help=(
            "Path to the project root; the spec runner is invoked from "
            "this directory."
        ),
    )
    parser.add_argument(
        "--lemmas-file",
        type=Path,
        required=True,
        help=(
            "Path to the K lemmas file, relative to --project-root "
            "(e.g. test/kontrol/lemmas.k)."
        ),
    )
    parser.add_argument(
        "--spec-runner",
        type=Path,
        required=True,
        help=(
            "Path to the spec runner script "
            "(e.g. scripts/kontrol-lemma-test.sh). Invoked as "
            "'<spec-runner> <spec-stem>' from --project-root."
        ),
    )
    parser.add_argument(
        "--spec-stem",
        required=True,
        help="Spec stem passed as the sole argument to --spec-runner.",
    )
    parser.add_argument(
        "--expected-passes",
        type=int,
        required=True,
        help="PROOF PASSED count when every claim in the spec passes.",
    )
    parser.add_argument(
        "rules",
        nargs="+",
        help="Rule names to probe, in the desired order.",
    )
    parser.add_argument(
        "--pristine",
        type=Path,
        default=None,
        help=(
            "Optional pristine copy of the lemmas file; if given, the "
            "lemmas file is restored from it before the run starts."
        ),
    )
    parser.add_argument(
        "--results-file",
        type=Path,
        default=None,
        help=(
            "Output TSV log path (default: a fresh per-run file under "
            "$TMPDIR/minimize-lemmas-XXXXXX/results.tsv). Note the "
            "lemmas file is mutated in place with no locking; "
            "concurrent runs are only safe across distinct "
            "--lemmas-file targets."
        ),
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help=(
            "Scratch path used to restore the lemmas file after a "
            "NECESSARY verdict (default: a fresh per-run file under "
            "$TMPDIR/minimize-lemmas-XXXXXX/checkpoint.k)."
        ),
    )
    return parser


# Prefix for auto-generated scratch directories. Unique suffixes are
# appended by tempfile.mkdtemp so parallel invocations don't collide.
SCRATCH_PREFIX: Final[str] = "minimize-lemmas-"


def main() -> None:
    args = build_parser().parse_args()

    results_file: Path | None = args.results_file
    checkpoint: Path | None = args.checkpoint
    if results_file is None or checkpoint is None:
        run_tmpdir = Path(tempfile.mkdtemp(prefix=SCRATCH_PREFIX))
        print(f"scratch directory: {run_tmpdir}")
        if results_file is None:
            results_file = run_tmpdir / "results.tsv"
        if checkpoint is None:
            checkpoint = run_tmpdir / "checkpoint.k"

    sys.exit(
        minimize(
            project_root=args.project_root.resolve(),
            lemmas_file=args.lemmas_file,
            spec_runner=args.spec_runner,
            spec_stem=args.spec_stem,
            expected_passes=args.expected_passes,
            rules=list(args.rules),
            pristine=args.pristine.resolve() if args.pristine else None,
            results_file=results_file,
            checkpoint=checkpoint,
        )
    )


if __name__ == "__main__":
    main()
