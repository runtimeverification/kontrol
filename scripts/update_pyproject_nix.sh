#!/bin/bash

# Exit on error
set -e

# --- Configuration ---
UV2NIX_REPO="pyproject-nix/uv2nix"
PYPROJECT_BUILD_SYSTEMS_REPO="pyproject-nix/build-system-pkgs"
FLAKE_FILE="flake.nix"
TEST_PR_WORKFLOW_FILE=".github/workflows/test-pr.yml"
UPDATE_VERSION_WORKFLOW_FILE=".github/workflows/update-version.yml"

# --- Input Arguments ---
USER_UV2NIX_REV=$1
USER_PYPROJECT_BUILD_SYSTEMS_REV=$2

# --- Check for GITHUB_TOKEN ---
if [ -z "$GITHUB_TOKEN" ]; then
  echo "Error: GITHUB_TOKEN environment variable is not set."
  exit 1
fi

# --- Configure Git User ---
echo "Configuring Git user..."
git config user.name "devops"
git config user.email "devops@runtimeverification.com"

# --- Determine Revisions ---
echo "Determining revisions..."
if [ -z "$USER_UV2NIX_REV" ]; then
  echo "Fetching latest uv2nix commit SHA..."
  UV2NIX_REV=$(gh api "repos/$UV2NIX_REPO/commits/master" --jq .sha -H "Authorization: token $GITHUB_TOKEN")
else
  UV2NIX_REV="$USER_UV2NIX_REV"
fi
echo "Using uv2nix revision: $UV2NIX_REV"

if [ -z "$USER_PYPROJECT_BUILD_SYSTEMS_REV" ]; then
  echo "Fetching latest pyproject-build-systems commit SHA..."
  PYPROJECT_BUILD_SYSTEMS_REV=$(gh api "repos/$PYPROJECT_BUILD_SYSTEMS_REPO/commits/master" --jq .sha -H "Authorization: token $GITHUB_TOKEN")
else
  PYPROJECT_BUILD_SYSTEMS_REV="$USER_PYPROJECT_BUILD_SYSTEMS_REV"
fi
echo "Using pyproject-build-systems revision: $PYPROJECT_BUILD_SYSTEMS_REV"

# --- Update flake.nix ---
echo "Updating $FLAKE_FILE..."
sed -i -r 's|(url = "github:'"$UV2NIX_REPO"'/)[a-zA-Z0-9]+(")|'"$UV2NIX_REV"'|' "$FLAKE_FILE"
sed -i -r 's|(url = "github:'"$PYPROJECT_BUILD_SYSTEMS_REPO"'/)[a-zA-Z0-9]+(")|'"$PYPROJECT_BUILD_SYSTEMS_REV"'|' "$FLAKE_FILE"

# --- Update nix flake lock file ---
echo "Updating Nix flake lock file..."
nix flake lock

# --- Update uv version in GitHub workflows ---
echo "Fetching UV version from uv2nix revision $UV2NIX_REV..."
UV_VERSION=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "https://raw.githubusercontent.com/$UV2NIX_REPO/$UV2NIX_REV/pkgs/uv-bin/srcs.json" | jq .version -r)

if [ -z "$UV_VERSION" ] || [ "$UV_VERSION" == "null" ]; then
  echo "Error: Could not determine UV version. Please check the uv2nix revision and network connectivity."
  exit 1
fi
echo "Determined UV version: $UV_VERSION"

echo "Updating UV version in workflow files..."
SED_COMMAND="/uses: astral-sh\/setup-uv@v[0-9.]+/{ n ; /with:/{ n ; s/version: .*/version: "$UV_VERSION"/ } }"

if [ -f "$TEST_PR_WORKFLOW_FILE" ]; then
  sed -i -r "$SED_COMMAND" "$TEST_PR_WORKFLOW_FILE"
  echo "Updated $TEST_PR_WORKFLOW_FILE"
else
  echo "Warning: $TEST_PR_WORKFLOW_FILE not found. Skipping."
fi

if [ -f "$UPDATE_VERSION_WORKFLOW_FILE" ]; then
  sed -i -r "$SED_COMMAND" "$UPDATE_VERSION_WORKFLOW_FILE"
  echo "Updated $UPDATE_VERSION_WORKFLOW_FILE"
else
  echo "Warning: $UPDATE_VERSION_WORKFLOW_FILE not found. Skipping."
fi

# --- Create commit ---
echo "Creating commit..."
git add "$FLAKE_FILE" flake.lock
if [ -f "$TEST_PR_WORKFLOW_FILE" ]; then
  git add "$TEST_PR_WORKFLOW_FILE"
fi
if [ -f "$UPDATE_VERSION_WORKFLOW_FILE" ]; then
  git add "$UPDATE_VERSION_WORKFLOW_FILE"
fi

COMMIT_MESSAGE="update pyproject-nix and uv to v$UV_VERSION"
if git diff --staged --quiet; then
  echo "No changes to commit."
else
  git commit -m "$COMMIT_MESSAGE"
  # --- Push commit ---
  echo "Pushing commit..."
  git push
  echo "Script finished successfully."
fi 