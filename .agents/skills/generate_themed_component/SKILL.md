---
name: generate_themed_component
description: Generates or refactors Vue 3 components ensuring absolute compliance with runtime theming and strict marketplace interface contracts.
---

# Generate Themed Component

## 1. Enforce TypeScript Contracts
Every component must use explicit Vue 3 compile-time macros (`defineProps<{...}>()` and `defineEmits<{...}>()`). No loose or untyped props are allowed.

## 2. Tailwind v4 Theme Compliance
Absolutely zero hardcoded values (colors, spacing, sizing). All classes must use native Tailwind v4 dynamic theme variables or arbitrary values tied to CSS variables (e.g., `bg-primary`, `p-[var(--spacing-md)]`).

## 3. State & Accessibility Invariant
Interactive elements must cleanly define styles for all interaction states (`:hover`, `:focus-visible`, `:active`, `:disabled`) and loading conditions.

## 4. Preservation Principle
Ingest existing code (`LeftPanel`, `CustomDropdown`, `CancelModificationWarningPopUp`) and isolate cosmetic/token refactoring from established core business logic or state emulation.