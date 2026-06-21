# Alibaba Cloud deployment

The backend runs on **Alibaba Cloud ECS** and calls **Qwen-Plus on DashScope**
(Alibaba Cloud Model Studio) at runtime. The two files that demonstrate use of
Alibaba Cloud APIs/services:

- [`../../src/wormbase_memory/inference.py`](../../src/wormbase_memory/inference.py)
  — `QwenCloudClient` → DashScope OpenAI-compatible endpoint (the Qwen Cloud call).
- [`Dockerfile`](Dockerfile) + [`deploy.sh`](deploy.sh) — the ECS deployment.

## Steps

1. **Model Studio**: create an API key, claim hackathon credits, note your region
   (International = Singapore endpoint; Mainland = Beijing endpoint).
2. **ECS**: launch Ubuntu 22.04, install Docker, open port 8501.
3. **Deploy**:
   ```bash
   export ECS_HOST=root@<ecs-public-ip>
   export DASHSCOPE_API_KEY=sk-...
   bash infra/aliyun/deploy.sh
   ```
4. **Proof recording** (hackathon requirement): record
   `ssh $ECS_HOST 'docker exec wbm python scripts/smoke_dashscope.py'`
   returning a live Qwen-Plus reply, plus the UI at `http://<ecs-ip>:8501`.

## Optional: local-Qwen triage worker

Run a small Qwen on the ECS box for the cheap recall/triage cameo:
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:1.7b
# set WBM_USE_LOCAL_QWEN=1 and OLLAMA_BASE_URL in the container env
```
