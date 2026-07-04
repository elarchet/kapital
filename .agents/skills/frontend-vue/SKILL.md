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
- **Dense & Scalable Layout Design (75% Zoom)**:
  - When the layout needs to be condensed/scaled down, declare `html { font-size: 75%; }` in the global CSS to scale all `rem` values down proportionally.
  - Never use fixed pixel heights (e.g., `h-[96px]`) for primary header bars and logos; instead, use relative scaling values (e.g., `h-[6rem]`) to keep adjacent elements aligned horizontally across different scaling values.
  - To maximize data density, prefer tight vertical paddings (like `py-1.5` instead of `py-3`) and margins on navigational list elements.
- **Collapsed Sidebar/Navigation Centering Rules**:
  - Ensure all icons, logo initials, and avatar components align cleanly in the center when the navigation sidebar collapses.
  - Use conditional classes like `:class="store.sidebarCollapsed ? 'mr-0' : 'mr-2'"` to prevent right/left spacing shifts in collapsed state when label text is hidden.
  - Explicitly center flex elements in collapsed containers using `:class=\"{ 'justify-center w-full': store.sidebarCollapsed }\"`.
- **Popover Positioning in Collapsed Mode**:
  - Always verify absolute popovers (e.g. user profile menus) don't overflow off-screen when the parent sidebar collapses.
  - Use conditional coordinates, e.g. `:class=\"store.sidebarCollapsed ? 'left-2 translate-x-0' : 'left-1/2 -translate-x-1/2'\"`.

## 3. Subfolder Organization
- Avoid flat components directories. Place related components in logical subdirectories (e.g., `components/import/`, `components/portfolio/`).
- Never exceed ~400 lines in any Vue component.

## 4. Defensive Rendering & Orchestration
- **Optional Chaining**: When rendering dynamic rows, custom templates, or preview tables where keys/columns or data might be missing, always use optional chaining (`?.`) or fallback checks.
- **Composables Orchestration**: For complex UI panels or wizards (like the import wizard), do not pack all logic into a single component or hook. Separate concerns by orchestrating multiple focused sub-composables (e.g., separating executor, parser/processor, and UI mapping wizards) from the parent view/component.

## 5. Routing (Vue Router v5)
- The project uses **file-based routing** via Vue Router v5 built-in capabilities.
- All routes must be created as `.vue` files inside the `frontend/src/pages/` directory (e.g., `[id].vue` for dynamic parameters).
- Use the `definePage()` macro within the page component to define route metadata (e.g., `meta: { requiresAuth: true }`, or overriding route `name`).
- Do not manually register routes in `src/router/index.ts`.
