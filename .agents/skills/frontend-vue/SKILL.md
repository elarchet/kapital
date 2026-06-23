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
