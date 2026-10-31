# Publishing a public FinSight demo

There are two ways to host it, each with a different job. Most people should set up both. Total time is about 15 minutes.

| | **GitHub Pages: static demo** | **Hugging Face Space: live app** |
|---|---|---|
| URL | `https://streetsmartops.github.io/finsight2.0/` | `https://huggingface.co/spaces/<hf-user>/finsight` (app itself: `https://<hf-user>-finsight.hf.space`) |
| What runs | The real engines run at build time; questions are answered **in the visitor's browser** by a JS port of the retriever + template composer (proved identical by `tests/test_static_parity.py`) | The actual FastAPI container, the same image as `docker compose up` |
| Free-text questions | ✅ (template mode) | ✅ (template, or **Claude** if you add a key) |
| Always on | ✅ no cold start, nothing to sleep | ⚠️ free tier sleeps after ~48 h idle; first visit wakes it (~1 min) |
| Cost | free | free (CPU basic); Claude calls billed to your key |
| Best for | the LinkedIn link, recruiters, mobile | live interviews, showing the API, Claude mode |

Both deploy automatically from `main` through GitHub Actions once you finish the one-time setup below.

---

## A. GitHub Pages (about 3 minutes)

1. Merge this PR into `main`.
2. On GitHub, open **Settings → Pages → Build and deployment → Source** and choose **GitHub Actions**.
3. Open **Actions → "Deploy static demo (GitHub Pages)" → Run workflow**. This is only needed the first time; after that, every push to `main` redeploys.
4. When it goes green, open **https://streetsmartops.github.io/finsight2.0/**.

The workflow runs the full test suite before it publishes, so a broken engine or a mismatch between the JS and Python answers never ships.
To preview locally:
```bash
python demo/static/build.py --out site && python -m http.server -d site 8080   # http://localhost:8080
```

---

## B. Hugging Face Space (about 10 minutes)

1. **Create a Hugging Face account** at huggingface.co, if you don't have one. Your username goes in the Space URL.
2. **Create a write token:** go to huggingface.co → **Settings → Access Tokens → Create new token**, choose type **Write**, and name it `github-finsight`. Copy it.
3. **Add it to GitHub:** in the repo, open **Settings → Secrets and variables → Actions**.
   - **Secrets** tab → *New repository secret*: name `HF_TOKEN`, value: the token.
   - **Variables** tab → *New repository variable*: name `HF_SPACE`, value `<hf-username>/finsight`.
4. **Deploy:** open **Actions → "Deploy live demo (Hugging Face Space)" → Run workflow**.
   The script creates the Space if it doesn't exist (Docker SDK), sets `FINSIGHT_ASK_PER_MIN=20`, and uploads only the app (`Dockerfile`, `src/`, `api/`, `requirements.txt`, `LICENSE`) plus the Space card from `demo/hf_space/README.md`.
5. Watch the build in the Space's **Logs** tab. The first build takes about 3–5 minutes, then the app opens at `https://huggingface.co/spaces/<hf-username>/finsight`.

After that, pushes to `main` that touch the app redeploy automatically.

**Deploy from your laptop instead of Actions:**
```bash
pip install huggingface_hub
HF_TOKEN=hf_... python demo/hf_space/deploy.py --space <hf-username>/finsight
```

### Optional: turn on Claude in the Space
In the Space, open **Settings → Variables and secrets → New secret** and add `ANTHROPIC_API_KEY`. The Space restarts and the cockpit badge changes to **LLM grounded**.

Before you do, keep these in mind:
- Anyone with the URL can make you spend money. FinSight caps each visitor at **20 questions per minute** (`FINSIGHT_ASK_PER_MIN`, a Space variable) and questions at 500 characters. Also **set a monthly spend limit** in the Anthropic console, and use a key dedicated to this demo.
- The default model is set in `src/finsight/rag.py` (`FinSightRAG(model=...)`). Check that it's a model your key can use.
- If the key is missing, invalid or out of credit, FinSight falls back to template answers. The demo keeps working.

---

## C. After it's live

- [ ] Smoke-test the Space at its direct app URL (the Space page wraps the app in an iframe): `./demo/smoke_test.sh https://<hf-user>-finsight.hf.space`. Pages is static, so open it and ask the off-topic question instead.
- [ ] Add the links to the README, the LinkedIn post and your CV (the README "Live demo" line is already in place for Pages).
- [ ] Pin the Space on your Hugging Face profile, and pin the repo on your GitHub profile.
- [ ] If you share the Space link for a live session, open it 2 minutes beforehand to wake it up.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Pages workflow fails at *deploy* with "Pages not enabled" | Step A2: Source must be **GitHub Actions**, not "Deploy from a branch" |
| Pages shows a 404 for a few minutes | the first deploy can take up to 10 minutes to propagate |
| Space job prints "skipping Space deploy" | `HF_TOKEN` secret or `HF_SPACE` variable is missing or misspelled |
| Space job fails with 401/403 | the token is read-only. Create a **Write** token, or one with write access to that Space |
| Space build error mentioning port | `app_port: 8000` in `demo/hf_space/README.md` must match the container (it does by default) |
| Space shows "Sleeping" | expected on the free tier; any visit wakes it |
| Space answers say "LLM composition unavailable" | the key is invalid or out of credit, or the model name isn't available to the key. The template answer shown is still correct |
