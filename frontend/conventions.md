# Zebora — Frontend Conventions

Extends `general/conventions.md`. Applies to all frontend repos.

> **Status: skeleton — fill in after pulling details from the primary frontend
> repo.** The sections below are placeholders; replace them with real stack
> choices before tagging v1.0.0.

---

## Stack (fill in)

- Framework: _e.g. Next.js 15 App Router_
- Styling: _e.g. Tailwind CSS v4_
- State management: _e.g. Zustand / React Query / server components_
- API client pattern: _e.g. tRPC / fetch wrapper / OpenAPI-generated client_
- Component library: _e.g. shadcn/ui_
- Testing: _e.g. Vitest + React Testing Library + Playwright_

## File / folder conventions

```
app/                  # Next.js App Router pages and layouts (or src/app/)
  (routes)/
    page.tsx
    layout.tsx
components/
  ui/                 # Headless / base primitives (shadcn or similar)
  <feature>/          # Feature-scoped components
lib/
  api/                # API client / server actions
  utils/              # Pure utility functions (no React)
hooks/                # Custom React hooks
types/                # Shared TypeScript types
```

## Component rules

- One component per file.
- Co-locate the component's test: `Button.tsx` + `Button.test.tsx`.
- No business logic in components — extract to hooks or `lib/`.
- Prefer server components by default; add `"use client"` only when
  interactivity or browser APIs are required.

## Styling

- Use Tailwind utility classes directly on elements; no custom CSS unless
  Tailwind can't express it.
- No inline `style={{}}` except for truly dynamic values (e.g. chart widths).
- Consistent spacing scale: stick to Tailwind's default scale, don't introduce
  arbitrary pixel values.

## Data fetching

- Server components fetch data directly (no client-side fetch waterfalls).
- Mutations through server actions; client-side optimistic updates where UX
  demands it.
- Wrap external API calls in `lib/api/` — no naked `fetch` calls in components
  or pages.

## TypeScript

- `strict: true` in `tsconfig.json`. No `any` without an explanatory comment.
- Prefer `type` over `interface` for plain data shapes; use `interface` when
  declaration merging is needed.
- Exports from `lib/` and `hooks/` are named (not default) exports.

## Local dev

```sh
pnpm install
pnpm dev
```

Required env vars: see `.env.example` at repo root.
