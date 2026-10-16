# ADRs — identity

Decisions and the alternatives rejected, newest first. Replaces "best X" branches: an experiment ends here as a dated entry, not as a branch.

## 0003 · Invite-only by default (2026-10-16)
- Status: accepted
- Context: AveHealth is invite-only: nobody signs themselves up or picks their own role. Softball's shape is the same (league director → coach → parent → kid).
- Decision: `signup: invite-only` is the default; `open` exists for apps that want it.
- Alternatives rejected: Open sign-up by default: every multi-role app would need its own role-claim review.

## 0002 · One interface over Cognito and Supabase Auth (2026-10-16)
- Status: accepted
- Context: The owner wants multi-role apps on the free tier as well as on AWS.
- Decision: Cognito on aws, Supabase Auth on free, both behind `identity.*`. No code outside this module calls either SDK.
- Alternatives rejected: Cognito only (pushes multi-role apps off the free tier). Supabase only (AveHealth is live on Cognito).
- Consequences: `mfa: passkey` is aws-tier until Supabase Auth's passkey support is confirmed.

## 0001 · Module created from the contract (2026-10-16)
- Status: accepted
- Context: `identity` was defined in `docs/CONTRACT.md` from the AveHealth / softball paper split.
- Decision: the interfaces in `module.yaml` are the contract; implementation follows the extraction order in the contract doc.
- Alternatives rejected: keeping this capability inside each app (fails the two-app test the moment softball needs it).
