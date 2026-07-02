---
name: stacked-branches
description: |
  Stacked branch workflow: push current feature branch to trigger CI/CD and auto-PR, 
  then immediately scaffold the next branch on top without waiting for merge. 
  Handles housekeeping (prune gone branches, sync main silently) and rebase cascades 
  when a parent branch has merged. Trigger phrases: "next feature", "stack next", 
  "ready for next", "ship and continue", "push and stack".
---

# Stacked Branch Workflow

Instead of waiting for CI + merge before starting the next feature, stack the new branch
directly on top of the current one. The agent auto-detects whether to branch from `main`
or from a pending feature branch — no manual tracking needed.

---

## Housekeeping (run at conversation start, before creating any branch)

```bash
git fetch --prune                       # sync remote refs, mark deleted branches as [gone]
git fetch origin main:main              # fast-forward local main without checkout (skip if errors)
```

Delete local branches whose remote is gone, **only if fully merged**:

```bash
for branch in $(git branch -vv | grep ': gone]' | awk '{print $1}'); do
  if [ -z "$(git log origin/main..$branch --oneline)" ]; then
    git branch -D "$branch"
  else
    echo "⚠ Skipping $branch — has unmerged local commits"
  fi
done
```

---

## Auto-detect: branch from `main` or stack?

After housekeeping, check for feature branches that still have an active remote (pending PR):

```bash
# List local branches (not main) that have an active upstream (not [gone])
git branch -vv | grep -v '^\*\?\s*main ' | grep 'origin/' | grep -v ': gone]'
```

- **No pending branches** → previous work is merged. `git checkout main`, then branch from `main`.
- **One pending branch** → its PR hasn't merged yet. Stack the new branch on top of it.
- **Multiple pending branches** → ask the user which one to stack on (shouldn't happen often).

This detection replaces any need for metadata files or git config — the state is readable
directly from `git branch -vv` at every conversation start.

---

## Push & Stack

1. **Commit** current work following the [git-commit](file:///home/etien/dev/perso/kapital/.agents/skills/git-commit/SKILL.md) skill (all commit rules live there).

2. **Push** to trigger CI and auto-PR:
   ```bash
   git push -u origin $(git branch --show-current)
   ```

3. **Ask** the user for the next feature name. Convention: `feat/<kebab-case>`.

4. **Scaffold** the new branch on top of the current one (not main):
   ```bash
   git checkout -b feat/<next-feature>
   ```

---

## Rebase Cascade (when the stacked parent merges)

Triggers when housekeeping detects that a branch's upstream is gone while you're on a
branch that was stacked on top of it — i.e., the parent merged into main.

```bash
git rebase main
git push --force-with-lease
```

If rebase has conflicts: **stop, report the conflicting files, wait for user to resolve.**

---

## Guardrails

- **On `main`?** Refuse to push. Ask which feature branch to use.
- **Uncommitted changes?** Commit first (with approval) or stash if user prefers.
- **`prek` fails?** Do not push. Fix first.
- **`fetch origin main:main` errors?** Warn and skip — proceed with push/stack.
