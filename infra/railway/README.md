# Railway Deployment

Deploy both services (web + api) on Railway.

## Setup

1. Create a new Railway project
2. Add two services from the same repo:

### Web Service (Next.js)
- **Root Directory**: `apps/web`
- **Build Command**: `pnpm install && pnpm build`
- **Start Command**: `pnpm start`
- **Port**: `3000`

### API Service (FastAPI)
- **Root Directory**: `services/api`
- **Build Command**: `pip install -r requirements.txt && pip install -r requirements-ml.txt && python scripts/setup_rife.py`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

> **Resource notes.** Interpolation is CPU/GPU-heavy and long-running. The `requirements-ml.txt`
> install pulls **torch + OpenCV** (a large image); provision generous build storage and RAM.
> ffmpeg is bundled via `imageio-ffmpeg` (no system package). The engine auto-detects
> CUDA → Apple MPS → CPU and defaults to **CPU** — a CPU-only container works, but a render of a
> long clip is slow; keep `MAX_SOURCE_FRAMES` modest or attach a GPU. Renders run in a background
> thread, so use a persistent instance (not a scale-to-zero worker) while jobs are in flight.
> Use a **Python 3.11** base image (a RIFE constraint).

## Environment Variables

Set these on the API service:

| Variable | Value |
|----------|-------|
| `B2_APPLICATION_KEY_ID` | Your B2 application key ID |
| `B2_APPLICATION_KEY` | Your B2 application key |
| `B2_BUCKET_NAME` | Your bucket name |
| `B2_REGION` | Your bucket region (e.g. `us-west-004`) — drives the S3 endpoint |
| `API_CORS_ORIGINS` | Your web service URL (e.g., `https://web-production-xxx.up.railway.app`) |

Set this on the Web service:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Your API service URL (e.g., `https://api-production-xxx.up.railway.app`) |
