#!/usr/bin/env bash
# Kompile + prove a lemma-test spec against a freshly-built minimal
# definition (no Solidity). See the writing-kontrol-lemmas skill for the
# underlying workflow.
#
# Usage:
#   scripts/kontrol-lemma-test.sh <spec-stem>           # e.g. keccak-slots-disjoint
#   scripts/kontrol-lemma-test.sh <stem> <MODULE>       # override spec module name
#
# The spec file lives at ${SPEC_DIR}/<stem>-spec.k and the spec module
# defaults to uppercase(<stem>)-SPEC (kebab case preserved).
#
# We invoke the `kevm` wrapper that `kontrol` itself depends on (resolved
# from kontrol's nix-store closure), not whichever `kevm` happens to be
# first on PATH — kontrol pins the matching kevm version. The wrapper
# already exports:
#   - PATH (adds the matching `k` binary),
#   - KDIST_DIR (pre-built evm-semantics.plugin/krypto.a for llvm-library),
#   - NIX_LIBS  (-L flags for openssl/secp256k1, needed by llvm-kompile).
# So the script only has to worry about -I include paths for the K source
# (.md) files that the spec's definition transitively imports.
set -euo pipefail

cd "$(dirname "$0")/.."

# ─── PROJECT-SPECIFIC paths — edit these to match your layout ────────────
SPEC_DIR="test/kontrol/lemma-tests"        # where <stem>-spec.k files live
LEMMAS_DIR="test/kontrol"                  # directory containing the lemmas file
LEMMAS_BASENAME="lemmas.k"                 # filename `run-lemma.k` requires (edit if renamed)
DEFN_DIR="out/lemma-tests-kompiled"        # kompiled definition output dir
PROOFS_DIR="out/proofs-lemma-tests"        # kevm prove state dir
# ─────────────────────────────────────────────────────────────────────────

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <spec-stem> [SPEC-MODULE]" >&2
  exit 2
fi

stem="$1"
spec_file="${SPEC_DIR}/${stem}-spec.k"

if [[ ! -f "$spec_file" ]]; then
  echo "error: spec file not found: $spec_file" >&2
  exit 1
fi

# Verify the lemmas file `run-lemma.k` requires is reachable via -I
# $LEMMAS_DIR. K's include resolver silently tries many paths, so a
# typo here surfaces as a confusing parser error during kompile —
# catch it up front.
if [[ ! -f "$LEMMAS_DIR/$LEMMAS_BASENAME" ]]; then
  echo "error: lemmas file not found at \$LEMMAS_DIR/\$LEMMAS_BASENAME = $LEMMAS_DIR/$LEMMAS_BASENAME" >&2
  echo "       (edit LEMMAS_DIR / LEMMAS_BASENAME at the top of this script," >&2
  echo "        and the 'requires' line in $SPEC_DIR/run-lemma.k, to match)" >&2
  exit 1
fi

# Default module name: uppercase stem + -SPEC. Kebab case is preserved.
default_module="$(echo "$stem" | tr '[:lower:]' '[:upper:]')-SPEC"
spec_module="${2:-$default_module}"

# --- Resolve nix store paths from the kontrol in PATH ---------------
# Hardcoded store paths go stale on every kontrol rebuild. Instead,
# walk kontrol's direct runtime references: its closure pins both the
# matching `kevm` and `kontrol-pyk-env` (the latter ships `kontrol` and
# `kevm_pyk` as Python packages, which is where the .md source files we
# need to `-I`-include actually live).
for tool in kontrol nix-store; do
  if ! command -v "$tool" >/dev/null; then
    echo "error: $tool not found in PATH" >&2
    exit 1
  fi
done

kontrol_bin="$(readlink -f "$(command -v kontrol)")"
kontrol_pkg="${kontrol_bin%/bin/kontrol}"
if [[ "$kontrol_pkg" == "$kontrol_bin" ]]; then
  echo "error: resolved kontrol path does not end in /bin/kontrol: $kontrol_bin" >&2
  exit 1
fi

# Walk kontrol's references once, picking out both packages we need.
# For kevm we also require `bin/kevm` to exist — a plain `kevm-*` glob
# would otherwise match `kevm-pyk` / `kevm-pyk-env` (the pure-python
# package with no wrapper binary, which doesn't export the KDIST_DIR /
# NIX_LIBS env vars the kompile step relies on).
kontrol_pyk_env=""
kevm_pkg=""
while IFS= read -r ref; do
  base="${ref##*/}"
  name="${base#*-}"
  if [[ -z "$kontrol_pyk_env" && "$name" == "kontrol-pyk-env" ]]; then
    kontrol_pyk_env="$ref"
  elif [[ -z "$kevm_pkg" && "$name" == kevm-* && -x "$ref/bin/kevm" ]]; then
    kevm_pkg="$ref"
  fi
done < <(nix-store -q --references "$kontrol_pkg")

if [[ -z "$kontrol_pyk_env" ]]; then
  echo "error: kontrol-pyk-env not in kontrol's references ($kontrol_pkg)" >&2
  exit 1
fi
if [[ -z "$kevm_pkg" ]]; then
  echo "error: no kevm-* with bin/kevm in kontrol's references ($kontrol_pkg)" >&2
  exit 1
fi

# site-packages lives under an unpredictable python3.X dir.
shopt -s nullglob
site_packages_candidates=("$kontrol_pyk_env"/lib/python*/site-packages)
shopt -u nullglob
if (( ${#site_packages_candidates[@]} == 0 )); then
  echo "error: no site-packages under $kontrol_pyk_env/lib/python*/" >&2
  exit 1
fi
site_packages="${site_packages_candidates[0]}"

KDIST_KONTROL="$site_packages/kontrol/kdist"
KEVM_SEM="$site_packages/kevm_pyk/kproj/evm-semantics"
KEVM_PLUGIN="$site_packages/kevm_pyk/kproj/plugin"
kevm_bin="$kevm_pkg/bin/kevm"

for p in "$KDIST_KONTROL" "$KEVM_SEM" "$KEVM_PLUGIN" "$kevm_bin"; do
  if [[ ! -e "$p" ]]; then
    echo "error: expected path missing after dep resolution: $p" >&2
    exit 1
  fi
done

echo "=== kevm kompile-spec ($spec_file → $DEFN_DIR, with llvm-library) ==="
# `--with-llvm-library` builds the LLVM booster interpreter into
# $DEFN_DIR/llvm-library/, which `kevm prove` picks up so the booster can
# discharge simplification side conditions in-memory instead of
# round-tripping every check to Z3 (an order-of-magnitude speedup on
# keccak/Map side conditions).
"$kevm_bin" kompile-spec "$spec_file" \
    --main-module VERIFICATION \
    --syntax-module VERIFICATION \
    --output-definition "$DEFN_DIR" \
    --emit-json \
    --with-llvm-library \
    -I "$LEMMAS_DIR" -I "$SPEC_DIR" \
    -I "$KDIST_KONTROL" -I "$KEVM_SEM" -I "$KEVM_PLUGIN"

echo
echo "=== kevm prove ($spec_module) ==="
# --reinit: discard cached proof state in $PROOFS_DIR.
"$kevm_bin" prove "$spec_file" \
    --definition "$DEFN_DIR" \
    --spec-module "$spec_module" \
    -I "$LEMMAS_DIR" -I "$SPEC_DIR" \
    -I "$KDIST_KONTROL" -I "$KEVM_SEM" -I "$KEVM_PLUGIN" \
    --save-directory "$PROOFS_DIR" \
    --reinit
