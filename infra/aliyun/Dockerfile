# Backend image for Alibaba Cloud ECS (or Function Compute / ACK).
# Runs the Streamlit UI + agent; calls Qwen-Plus on DashScope at runtime.
FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY src ./src
COPY ui ./ui
COPY data ./data
RUN uv pip install --system -e ".[ui]"

EXPOSE 8501
# DASHSCOPE_API_KEY is injected at runtime (ECS env / Secrets Manager).
CMD ["streamlit", "run", "ui/app.py", \
     "--server.port=8501", "--server.address=0.0.0.0"]
