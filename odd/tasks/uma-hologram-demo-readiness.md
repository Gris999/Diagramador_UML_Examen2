# Verify deployed Uma and restore the local AI demo

## Objective and why
Make Uma and hologram proposals demonstrable on diagramador.dev and restore the local diagram editor with genuine Ollama inference before the university partial.

## Authorized scope
- User explicitly authorized discovery and use of this project's existing SSH access to diagramador.dev, deployment of Uma/hologram and local AI startup.
- Authorized remote destination: diagramador.dev, currently 18.188.167.127; SSH user ubuntu using the discovered project identity file. Never record key contents/passwords or use unrelated agents/sessions.
- Use explicit identity, disable SSH-agent and multiplex reuse, require existing host-key verification.
- Preserve diagrams, databases, environment secrets and unrelated staged Flutter work. Do not push, merge, upgrade dependencies or download another model.
- Only restart/rebuild production if verified evidence shows the published implementation is missing or stale; back up current commit/images first and keep a rollback route. No unnecessary production changes.
- Current feature branch is fix/flutter-home-card-overflow; retain it to preserve unrelated uncommitted/staged work. Deploy only committed intended code, never the working tree wholesale.

## Exploration findings
- Production SSH read-only verification: /home/ubuntu/Diagramador_UML_Examen2, HEAD4cddf7e (PR35 Uma/hologram). Tracked tree clean; existing untracked environment backups left untouched. Six application/database containers running. Root disk4GB available; available memory1158MB. No rebuild warranted yet.
- docs/DESPLIEGUE.md records successful deployment at 2026-11-10 00:30 Bolivia; GAP_MATRIX RF42-45 still says not deployed and is stale.
- Mac: Ollama installed and qwen3.5:9b cached; Ollama11434, Django8000 and Angular4200 stopped; Docker Desktop stopped. Local .env uses Docker DB/cache hostnames; native backend needs explicit loopback runtime overrides.
- TDDstrict OFF per docs/AI_CONTEXT.md. This is operations/verification, not new behavior; use targeted functional checks. RDDdisabled/unmanaged (off/default), no native reviews.
- Delivery strategy ask-on-risk; forecast approximately120 authored documentation lines, no application source changes expected. Work-unit commits must include only this feature's evidence/docs, never unrelated staged Flutter changes. Existing GGA hook must not be bypassed without explicit permission.

## Tasks
- [x] **DEMO-01** — Verify deployed Uma/hologram and correct stale deployment evidence.
  - Acceptance: published frontend includes the feature, backend chat route exists and a fresh demo room shows an Uma proposal/hologram when the provider responds; record actual failures and gaps. If already deployed, explicitly report no deployment/restart needed.
  - Checks: remote tracked HEAD/build identity, public page/API smoke and browser proposal preview/apply path. No production data deletion; leave any new test room clearly named.
  - Rollback: N/A for read-only verification; if deployment becomes necessary, snapshot images/commit before restart.
  - Observed: remote HEAD4cddf7e; committed application code matches local HEAD50b28ed (no application diff); public auth config200 and new chat route401 without session; full smoke script ends "Todo en orden". Browser production room `554be50e-0a8e-4be9-bc15-b07d9f11f1f2` named "Ensayo parcial - Uma y holograma": real Gemini proposal creates a Cliente preview/hologram; explicit Apply creates the class and Uma confirms. No production deployment/restart/migration was necessary. RF42-45 stale deployment statuses corrected; no claim of new manual routing/three-person test.
  - Work-unit commit: `3a46df7` (docs/deployment evidence only; native hook had no matching code files). RDDdisabled/unmanaged.
- [ ] **DEMO-02** — Start local services using the existing model and verify the real local proposal flow.
  - Acceptance: Ollama11434, PostgreSQL5433, Redis6379, Django8000, Angular4200 ready; local provider reports Ollama/qwen3.5:9b; a real local request returns a valid proposal. Preserve the user's data and ports; keep processes available for the demo.
  - Checks: installed-model list, Redis/DB readiness, Django check, local HTTP/provider endpoint and browser Uma/hologram behavior where tools permit. Never substitute a fake model response for inference evidence.
  - Rollback: stop only newly started native demo processes; do not remove volumes/data or stop unrelated services. No persistent .env changes are planned.
  - Observed: existing Docker Desktop, postgres_db and redis_server started; RedisPONG, local DB ready. Before applying existing additive collab0006/0007, a55KB custom-format backup was verified at `/tmp/uma-local-db-before-migrate-20261110-1523.dump`, mode600. Both migrations applied successfully; no production migrations.
  - Runtime only: native Ollama PID7144 (session78958), Daphne PID7793 (session52961; `/tmp/software1-local-django-demo.log`), Angular PID7577 (session1972; `/tmp/software1-local-angular-demo.log`). Loopback listeners11434/8000/4200 verified. No .env/source changes or model downloads; existing qwen3.5:9b loaded (Ollama API ps runnermlx).
  - Real browser result: local room `0fc2eb2f-7253-4df0-9911-980f3cce927e` at http://localhost:4200 shows Local(qwen3.5:9b) selected. "Uma, agrega una clase Producto con nombre y precio" returns a valid proposal and purple dashed hologram (Producto, nombre:String, precio:Number). Left pending for the user's demo, with Apply/Discard buttons visible. This is actual inference, not a stub; production proposal/apply separately verified underDEMO-01.
  - Rollback: stop only PIDs7144/7793/7577 if needed; do not drop databases/volumes or reverse migrations over existing data without reviewing backup/consumers.
  - Work-unit commit: pending documentation commit; RDDdisabled/unmanaged.

## Progress
- Both production and local runtime outcomes observed. No production deployment/restart/migration performed; existing feature was already published.
- Prior relevant checks: Angular648, Django648 with actual PG/Redis/Mongo, Spring12 passed. These are earlier results, not fresh runtime evidence.
- Mirror: full initial document saved/read back as Engram#379; same observation reused for progress.
- Authored committed line count:63 in `3a46df7` (59 additions/4 deletions, docs only). No PR/push authorized.

## Next step
Commit the local startup evidence/docs, then record the commit and leave both demo tabs and local services available. No further heavy tests needed before the partial.
