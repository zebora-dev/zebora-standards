# Zebora — Frontend Conventions

Extends `general/conventions.md`. Applies to all frontend repos.

Two distinct frontend contexts exist at Zebora:

| Repo | Purpose | Notes |
|---|---|---|
| `zebora-marketing` | Public marketing site (zebora.io) | Single Next.js app |
| `banrd-llm` | Client dashboard + internal admin | Turborepo monorepo, two apps |

Both share the same stack and the conventions below unless a section explicitly
calls out a difference.

---

## Stack

| Concern | Choice |
|---|---|
| Framework | Next.js (App Router) — marketing on 14.x, banrd-llm on latest |
| Language | TypeScript 5, `strict: true` |
| Styling | Tailwind CSS v4 |
| Component primitives | Radix UI (unstyled) + shadcn/ui conventions |
| Icons | Lucide React / Radix Icons |
| Forms | react-hook-form + zod (`@hookform/resolvers`) |
| Data fetching | Server components by default; React Query / SWR for client-side polling |
| State (banrd-llm) | Redux Toolkit for global app state; server components for read-heavy data |
| Auth / DB | Supabase (`@supabase/ssr` + `@supabase/supabase-js`) |
| AI features (banrd-llm) | Vercel AI SDK v6 (`ai`, `@ai-sdk/openai`, `@ai-sdk/react`) |
| Analytics | Vercel Analytics + PostHog (banrd-llm dashboard) |
| Error monitoring | Sentry (`@sentry/nextjs`) |
| CMS (marketing) | Contentful |
| Package manager | pnpm — always commit `pnpm-lock.yaml` |
| Monorepo tooling (banrd-llm) | Turborepo; shared packages under `packages/` |
| Linting / formatting | ESLint + Prettier (marketing); Biome + ultracite (banrd-llm) |
| Testing | Jest + React Testing Library (marketing); Vitest (banrd-llm) |

---

## Project layout

### Single app (zebora-marketing)

```
app/                  # App Router pages and layouts
  (routes)/
    page.tsx
    layout.tsx
components/
  ui/                 # shadcn/Radix primitives
  <feature>/          # Feature-scoped components
lib/
  api/                # Contentful client, server actions, API wrappers
  utils/              # Pure utility functions (no React)
hooks/                # Custom React hooks
```

### Monorepo (banrd-llm)

```
apps/
  dashboard/          # Client-facing portal
  admin/              # Internal admin tool
packages/
  ui/                 # @repo/ui — shared component library
  <other-shared>/
turbo.json
pnpm-workspace.yaml
```

Shared UI lives in `packages/ui` and is imported as `@repo/ui`. Never duplicate
a component across `apps/dashboard` and `apps/admin` — extract to the shared
package.

---

## Component rules

- One component per file. Filename matches the exported component name.
- Co-locate the test: `Button.tsx` + `Button.test.tsx`.
- No business logic in components — extract to hooks (`hooks/`) or `lib/`.
- Prefer server components. Add `"use client"` only when interactivity or
  browser APIs are genuinely required (event handlers, `useState`, `useEffect`,
  browser-only libraries).
- Use `cn()` (clsx + tailwind-merge) for conditional class composition.

## Styling

- Tailwind utility classes directly on elements.
- No inline `style={{}}` except for truly dynamic values (e.g. chart dimensions).
- No custom CSS files unless Tailwind can't express the rule.
- Consistent spacing: Tailwind's default scale only — no arbitrary `[42px]`
  values unless there's no alternative.
- Animations via `tailwindcss-animate` or Framer Motion — not raw CSS keyframes.

## TypeScript

- `strict: true` everywhere. No `any` without a comment explaining why.
- Prefer `type` for plain data shapes; `interface` only when declaration
  merging is needed.
- Named exports from `lib/` and `hooks/` — no default exports except for
  Next.js pages and layouts (required by the framework).
- Validate all external data (API responses, form input) with zod schemas at the
  boundary — never trust untyped JSON inside the app.

## Data fetching

- Server components fetch directly (async component + `await`). No
  client-side fetch waterfalls for initial page data.
- Mutations through Next.js server actions; use optimistic updates on the
  client only when the UX clearly requires it.
- Wrap all external API calls in `lib/api/` — no naked `fetch` calls in
  components or pages.
- Supabase client: use `@supabase/ssr` helpers; never share a single client
  instance across requests.

## Forms

- All forms use `react-hook-form` with a zod schema resolver.
- The zod schema is the single source of truth for field types and validation
  messages — don't duplicate validation logic in server actions.

## AI features (banrd-llm only)

- Use Vercel AI SDK v6 (`ai` package). Stream responses via `useChat` /
  `useCompletion` on the client; run model calls in Next.js route handlers or
  server actions.
- Don't call AI provider APIs directly from components.

## Error handling

- Use Sentry for unhandled exceptions; wrap top-level layouts with the Sentry
  error boundary.
- User-facing errors surface via `sonner` toasts — never raw `alert()`.
- Form errors surface inline via react-hook-form's `fieldState.error`.

## Linting / formatting

- **marketing:** ESLint (`eslint-config-next`) + Prettier. Run via husky
  pre-commit hooks.
- **banrd-llm:** Biome (ultracite config) + Prettier. Run via husky. Biome
  replaces ESLint and most Prettier rules — don't add ESLint to banrd-llm.
- CI must pass lint before merge.

## Testing

- Unit/integration: Jest + React Testing Library (marketing) or Vitest
  (banrd-llm).
- New UI behaviour ships with at least one component test.
- Don't test implementation details — test what the user sees and can do.
- E2E: Playwright (add to a repo if not already present before shipping
  critical user flows).

## Local dev

```sh
# marketing
pnpm install
pnpm dev

# banrd-llm (from repo root)
pnpm install
pnpm dev          # runs both apps via Turborepo
pnpm dev --filter=dashboard   # single app
```

Required env vars: see `env.example` / `.env.example` at repo root.
Copy to `.env.local` (gitignored). Never commit `.env.local`.
