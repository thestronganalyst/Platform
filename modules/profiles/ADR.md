# ADRs — profiles

Decisions and the alternatives rejected, newest first. Replaces "best X" branches: an experiment ends here as a dated entry, not as a branch.

## 0003 · Guardian-only accounts under 18, no private messaging with minors, three kid sign-ins (2026-10-17)
- Status: accepted
- Context: ADR 0002 left open how a kid signs in. The owner wants several options, parents to invite kids up to an age, and no private messaging between or with children. The youth-sports standard (SafeSport's MAAPP) allows an adult to message one athlete if a parent or another adult is copied; the owner's rule is stricter. COPPA's amended rule has applied in full since 2026-04-22 (a published retention policy and a written security program among its requirements).
- Decision:
  - `guardian_required_under: 18`: below it only a guardian creates the profile and issues the login. Configurable per app, never below 13.
  - A conversation that includes a minor (under 18) is never one-to-one; a group with a minor includes that minor's guardians. Enforced in Postgres through `profiles.safeguarding@1`, which every messaging module requires.
  - Minors read team conversations and announcements but do not post (`minors_post: false`), to start.
  - Kid sign-in methods built first: `pairing_code`, `parent_device`, `own_email` (13 and up). Each guardian picks per kid from what the app allows.
  - Team staff must be adults a league director has marked cleared (tenancy ADR 0004).
- Alternatives rejected: Guardian-only under 13 or 16 (two lines to explain; the messaging rule already treats everyone under 18 as a minor). MAAPP-style copied one-to-one messages (allowed by the standard, but a league can get it wrong; a ban cannot). Minors posting from the start (can be turned on later; harder to take back). Passkey first (needs a relying-party domain per app; pairing covers the same need now).
- Proposed with this decision, not yet confirmed by the owner (confirm when the module is built): kids see teammates as first name, last initial and jersey number only; photo consent per kid, off by default; nothing about a minor in public pages, search or a league-wide directory; no address or phone on a kid's profile; guardians can pause a login, sign out every device, see the kid's view and delete the kid's data; two guardians manage equally and a league director can restrict one (custody orders); a "report a concern" button that reaches the league's safety contact, not the coach; no ads, trackers or purchases in a kid's session; kid data deleted a set time after leaving the league, with every view or change audited.
- Consequences: `managed_age_threshold` and `managed_logins` are replaced by `guardian_required_under`, `kid_sign_in`, `own_email_from_age` and `minors_post`. The validator now checks array items against an enum and integer minimums. Counsel still confirms that a guardian creating the profile meets COPPA's verifiable-parental-consent standard before kids under 13 use the app.

## 0002 · Kids log in through a guardian-issued restricted login (2026-10-16)
- Status: accepted
- Context: The owner wants kids to log in and see games. Under 13, COPPA requires verifiable parental consent before collecting a child's personal information.
- Decision: A kid is a managed profile. Their guardian may issue them a read-only login scoped to their teams; the guardian's act of issuing it is the consent step, recorded in the audit stream.
- Alternatives rejected: Profile-only, no kid logins (owner wants kids in). Kid self sign-up (no parental consent step).
- Consequences: Before kids under 13 use it, counsel confirms the guardian-issued login meets COPPA's verifiable-parental-consent standard. How a kid signs in (passkey on a family device, a guardian-generated code) is decided when the module is built.

## 0001 · Module created from the contract (2026-10-16)
- Status: accepted
- Context: `profiles` was defined in `docs/CONTRACT.md` from the AveHealth / softball paper split.
- Decision: the interfaces in `module.yaml` are the contract; implementation follows the extraction order in the contract doc.
- Alternatives rejected: keeping this capability inside each app (fails the two-app test the moment softball needs it).
