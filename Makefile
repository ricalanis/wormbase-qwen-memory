# Run targets. Each baked with the correct uv extras + project context, so they
# work from ANY directory (uv's --extra is ignored unless uv is operating on the
# project; --directory pins it). Usage:  make ui   /   make -C path/to/repo ui
REPO := $(patsubst %/,%,$(dir $(realpath $(firstword $(MAKEFILE_LIST)))))
UV   := uv run --directory $(REPO)

.PHONY: help setup test demo ui cloud-demo prove curve triage seed mcp smoke
help:
	@echo "make setup       install all extras into the project venv"
	@echo "make test        run the test suite"
	@echo "make demo        offline 3-session CLI demo"
	@echo "make ui          Streamlit demo (planner = rules/Qwen-Plus per env)"
	@echo "make cloud-demo  Streamlit demo with planner = Qwen on Ollama Cloud"
	@echo "make prove       reproducibility + tamper-break"
	@echo "make curve       smarter+cheaper-over-sessions chart -> results/"
	@echo "make triage      local-Qwen triage cameo"
	@echo "make seed        persist a ledger for the MCP server"
	@echo "make mcp         run the MCP server (Claude Desktop / Cursor)"

setup:
	uv sync --directory $(REPO) --extra dev --extra ui --extra viz --extra mcp

test:
	$(UV) pytest -q

demo:
	$(UV) python scripts/run_demo.py

ui:
	$(UV) --extra ui --extra viz streamlit run ui/app.py

cloud-demo:
	WBM_PROVIDER=ollama_cloud $(UV) --extra ui --extra viz streamlit run ui/app.py

prove:
	$(UV) python scripts/prove_it.py

curve:
	$(UV) --extra viz python scripts/plot_curve.py

reliability:
	$(UV) --extra viz python scripts/plot_reliability.py

tune-escalation:
	$(UV) python scripts/tune_escalation.py

triage:
	WBM_USE_LOCAL_QWEN=1 $(UV) python scripts/triage_demo.py

seed:
	WBM_LEDGER_DB=$(REPO)/wbm_ledger.db $(UV) python scripts/seed_ledger.py

mcp:
	WBM_LEDGER_DB=$(REPO)/wbm_ledger.db $(UV) --extra mcp python -m wormbase_memory.mcp_server

smoke:
	$(UV) python scripts/smoke_dashscope.py
