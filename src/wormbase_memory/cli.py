"""`wbm-demo` entry point — run the 3-session memory/consistency demo."""

from __future__ import annotations

from .demo import run
from .inference import QwenCloudClient


def main() -> None:
    q = QwenCloudClient()
    print("WormBase Qwen Memory — data-ops MemoryAgent demo")
    print(f"planner backend   : {'Qwen-Plus (DashScope)' if q.available else 'deterministic rules (no DASHSCOPE_API_KEY)'}")
    print("=" * 78)
    run()


if __name__ == "__main__":
    main()
