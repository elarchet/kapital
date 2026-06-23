---
name: frontend-vue
description: Vue.js frontend architecture, decoupled data handling, and Tailwind CSS v4 styling rules.
---

# Vue.js Frontend & Tailwind CSS v4 Standards

This skill governs the development of the frontend single-page application (SPA).

## 1. Decoupled Presentation
- The frontend must never calculate PnL, aggregations, or financial projections. It must request these from the backend via the API and present them.
- Handle state and rendering cleanly. Use modern Vue 3 composition API (`<script setup>`).

## 2. Tailwind CSS v4 Design Tokens & Styles
- Always styling with Tailwind utility classes.
- Design tokens (colors, spacing, typography) must be declared once under the `@theme` directive in `frontend/src/style.css`.
- Avoid hardcoded custom spacing or raw color codes in the Tailwind classes.
- `<style scoped>` blocks in Vue files must be empty or near-empty. Never redeclare styles achievable via Tailwind utility classes.

## 3. Subfolder Organization
- Avoid flat components directories. Place related components in logical subdirectories (e.g., `components/import/`, `components/portfolio/`).
- Never exceed ~400 lines in any Vue component.

## 4. Defensive Rendering & Orchestration
- **Optional Chaining**: When rendering dynamic rows, custom templates, or preview tables where keys/columns or data might be missing, always use optional chaining (`?.`) or fallback checks.
- **Composables Orchestration**: For complex UI panels or wizards (like the import wizard), do not pack all logic into a single component or hook. Separate concerns by orchestrating multiple focused sub-composables (e.g., separating executor, parser/processor, and UI mapping wizards) from the parent view/component.
