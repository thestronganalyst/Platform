# identity

Login, sessions and roles. Cognito on the aws tier, Supabase Auth on the free tier, one interface either way. Invite-only by default.

- Pick it when: you need `identity.user@1`, `identity.session@1`, `identity.roles@1`.
- Status: `incubating` — aws tier built (Cognito pool, token verification, roles, invites, users table); deployed in the shell. Free tier, web/mobile screens, social sign-in and passkeys not yet.
- Source: AveHealth.

See `CLAUDE.md` for the contract and `ADR.md` for decisions.
