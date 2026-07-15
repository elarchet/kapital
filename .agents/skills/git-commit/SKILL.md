---
name: git-commit
description: Guide and rules for Git commits, permissions, conventional commits format, and local verification before committing.
---

# Git Commit Workflow & Conventions

This skill defines the strict protocol for creating git commits in the Kapital repository. It enforces permissions, author identity, formatting, and pre-commit checks.

## 1. Commit Permission & Push Restrictions
- **Explain Before Asking**: When you make changes, you MUST ALWAYS explain what you did FIRST. Never ask the user to authorize a git commit or push before you have fully explained the changes.
- **Zero Unsolicited Commits/Pushes**: You must **never** run any commit or push command without first presenting the proposed changes (e.g., in a git diff format or detailed list) and receiving explicit, written confirmation from the user.
- **Pushing to Feature Branches is Allowed**: You are allowed to push changes to remote feature branches (e.g., `git push origin <feature-branch>`) after receiving explicit user approval for the commits. Pushing directly to `main` remains strictly forbidden.

## 2. Execution Protocol
- Use standard `git commit` for all commits.
  - Example: `git commit -m "feat(api): add export endpoint"`

## 3. Conventional Commit Format
All commit messages must strictly comply with Conventional Commits rules to pass `commitizen check`:
- **Format**: `<type>(<scope>): <description>` (e.g., `feat(frontend): implement transaction filtering`)
- **Types**:
  - `feat`: A new feature
  - `fix`: A bug fix
  - `docs`: Documentation updates
  - `style`: Formatting, missing semi-colons, etc. (no production code change)
  - `refactor`: Refactoring code without behavior changes
  - `test`: Adding missing tests or correcting existing tests
  - `chore`: Updating build tasks, package manager configs, etc.
- **Rules**:
  - Use lowercase for type and scope.
  - Do not end the description with a period.
  - Keep the first line short (under 72 characters).

## 4. Atomic Commits
- Stage only specific changes relevant to the single logical unit of work.
- Use selective staging (e.g., `git add <file>` or `git add -p`) to avoid bundling unrelated modifications (e.g., temporary debug statements, unrelated refactoring) into a single commit.

## 5. Pre-Commit Checklist & Verification
Before requesting approval to commit, you must perform the following checks:
1. **Local Test Run**: Ensure all tests in the affected modules pass. Run `uv run pytest backend/tests/test_...` for backend or Playwright for frontend.
2. **Quality Control Hooks**: Run linting, quality, and verification checks (e.g., `prek` or equivalents running `ruff`, `ty`, `gitleaks`, and `commitizen`) to ensure zero errors prior to proposing the commit to the user.
3. **Size Budget check**: Confirm compliance with size budget and folder structures as detailed in [development-workflow](file:///home/etien/dev/perso/kapital/.agents/skills/development-workflow/SKILL.md).
4. **Ponytail Check**: Verify that YAGNI constraints are met and that any deliberate simplifications are marked with a `# ponytail:` comment per the guidelines in [ponytail.md](file:///home/etien/dev/perso/kapital/.agents/.rules/ponytail.md).
5. **Skill/Doc Reflection**: Explicitly ask yourself: "Can I add a skill with the new modification, should I update some existing skills, or should I update the README.md?" If your changes introduce new architectural patterns, tools, or workflows, update the relevant documentation before committing.
