# ADRs — web-shell

Decisions and the alternatives rejected, newest first. Replaces "best X" branches: an experiment ends here as a dated entry, not as a branch.

## 0002 · Stack: Vite, React 19, TypeScript, Tailwind 4, React Router, TanStack Query (2026-10-16)
- Status: accepted
- Context: AveHealth's web app runs this and deploys to S3 + CloudFront from CI.
- Decision: Keep it. Auth goes through Amplify on the aws tier and supabase-js on the free tier, both behind `identity.session@1`.
- Alternatives rejected: Next.js: needs a server runtime the free tier does not have, and AveHealth does not use it.

## 0001 · Module created from the contract (2026-10-16)
- Status: accepted
- Context: `web-shell` was defined in `docs/CONTRACT.md` from the AveHealth / softball paper split.
- Decision: the interfaces in `module.yaml` are the contract; implementation follows the extraction order in the contract doc.
- Alternatives rejected: keeping this capability inside each app (fails the two-app test the moment softball needs it).
