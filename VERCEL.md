# Vercel Deployment

The frontend and API are served from the same Vercel project. Keep the project root set to the repository root; `vercel.json` maps `/` and the static assets to `frontend/`, and routes `/v1/*` to `api/index.py`.

The frontend uses same-origin `/v1/*` requests by default. Set `VERA_API_BASE_URL` only when the API is hosted on a separate origin that permits the frontend through CORS. Do not set it to localhost in a production environment.

## Persistent Challenge Context

Vercel Functions can run in separate instances. Without a shared store, `/v1/context` data and tick suppression keys are held in instance memory and may not be available to a later invocation. The health endpoint identifies this as `"context_store": "instance-memory"`.

For durable context across function instances:

1. Create or connect an Upstash Redis/KV store to this Vercel project.
2. Make sure the Production environment has `KV_REST_API_URL` and `KV_REST_API_TOKEN` from that store. The application also accepts `VERA_KV_REST_URL` and `VERA_KV_REST_TOKEN` as aliases.
3. Redeploy after the variables are available.
4. Verify `GET /v1/healthz` returns `"context_store": "shared"`.

The local server can run without KV and reports `"context_store": "instance-memory"`; that is suitable for local development, not durable multi-instance challenge state.
