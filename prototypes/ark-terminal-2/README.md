# Ark Terminal 2.0 — standalone UI prototype

Approved six-screen UI, graphite palette. This directory is independent of the existing Ark Terminal runtime.

## Open
Open `public/index.html` directly in a browser. All JavaScript and CSS are embedded. No Higgsfield login, SDK, network connection, account credentials, or build dependencies are required.

## Vercel
Create a **separate project**, connected to `Iam-2squared/ark-terminal`.
- Branch: `ui/ark-terminal-2-standalone`
- Root Directory: `prototypes/ark-terminal-2`
- Framework Preset: Other
- Build Command: empty
- Install Command: empty
- Output Directory: `public`

The scoped `vercel.json` supplies those build settings. Do not change the existing Ark Terminal project's root directory or production branch. A direct files deployment can also use this directory unchanged; connecting Git for future automatic deployments is a separate project setting.

## Frozen UI snapshot
- HOME / SELECTOR / POSITIONS / ORDERS / PERFORMANCE / SYSTEM
- Approved palette: graphite, neutral text, restrained blue
- Exact copy of the reviewed standalone HTML; no behavior changes during relocation
- HTML SHA-256: `4d630234fc64c1b5d8df50851fde1989158e61a1db36d799d247fc8ae8f98870`
- Source provenance: Higgsfield website `b383221f-1e01-4e04-bf3a-b5b1aab02197`, palette revision `1b88610`; standalone font-import repair included

## Scope
All values and operations are synthetic UI demonstrations. No broker, RSS, research logic, account feeds, live execution, or paper execution is connected. Existing repository files are unchanged. This branch is not an approval to merge the UI into the live terminal or enable order execution.

The single HTML file contains the bundled React UI and styles. It is a portable distribution snapshot; a maintainable source-project migration is a subsequent step before substantive feature development.

## Rollback
The prototype is deployed separately. To roll it back, restore a previous deployment in its own Vercel project. The existing Ark Terminal runtime requires no rollback because it was not changed.
