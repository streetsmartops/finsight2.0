# Deploying FinSight for a shareable demo URL

All options use the root [`Dockerfile`](../../Dockerfile). The image is about 750 MB, runs as a non-root user, has a `HEALTHCHECK` and listens on `$PORT`.
It was verified locally with `docker build` and `docker run` plus [`smoke_test.sh`](../smoke_test.sh).

> **Security note:** the API has **no authentication** and CORS is `*`. The data is synthetic, so this is fine for a demo.
> Before pointing it at real billing data, put it behind SSO or an auth proxy (Cloudflare Access, IAP or oauth2-proxy) and restrict CORS.
> The `ANTHROPIC_API_KEY` is only ever read server-side.

| Target | Time to URL | Cost | Best for |
|---|---|---|---|
| Render (Blueprint) | ~5 min | free tier, sleeps when idle | async sharing, recruiters, reviewers |
| Fly.io | ~5 min | ~US$2–5/mo with one warm machine | live demo, India region (`bom`) |
| Google Cloud Run | ~5 min | scales to zero, pay per request | GCP shops |
| Any VM (EC2, Lightsail, DO) | ~10 min | VM price | full control, private network |

## Render
1. Push this repo to GitHub.
2. In Render, choose **New → Blueprint**, select the repo and set the path to `demo/deploy/render.yaml`.
3. Optionally set `ANTHROPIC_API_KEY`. Without it, FinSight runs in template mode.
4. Before presenting, warm it up: `./demo/smoke_test.sh https://<your-app>.onrender.com`

## Fly.io
```bash
fly launch  --config demo/deploy/fly.toml --dockerfile Dockerfile --no-deploy   # edit app name first
fly secrets set ANTHROPIC_API_KEY=sk-...                                          # optional
fly deploy  --config demo/deploy/fly.toml --dockerfile Dockerfile
./demo/smoke_test.sh https://finsight-demo.fly.dev
```

## Google Cloud Run
```bash
gcloud run deploy finsight --source . --region asia-south1 \
  --allow-unauthenticated --memory 1Gi --min-instances 1 \
  --set-env-vars ANTHROPIC_API_KEY=sk-...   # optional; prefer --set-secrets with Secret Manager
```
Cloud Run injects `$PORT` and the image honours it.

## Any VM with Docker
```bash
git clone <repo> && cd finsight2.0
ANTHROPIC_API_KEY=sk-... docker compose up -d --build      # or omit the key
./demo/smoke_test.sh http://<vm-ip>:8000
```
Put Caddy or nginx in front for TLS: `caddy reverse-proxy --from demo.example.com --to :8000`.

## Tear down after the demo
`fly scale count 0`, suspend the Render service, or `gcloud run services delete finsight`.
Then rotate any API key that was used.
