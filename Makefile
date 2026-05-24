# USAGE:
#   make up          — build images and start all containers
#   make down        — stop and remove containers
#   make test        — run the full pytest suite
#   make monitor     — start health monitor (Ctrl+C to stop)
#   make report      — generate HTML report from last test run
#   make logs        — show logs from all fw nodes
#   make status      — quick VIP and container status check
#   make clean       — stop containers and remove all volumes/images
# =============================================================================

# Shell to use for all recipes
SHELL := /bin/bash

# Project settings
COMPOSE       := docker compose
PYTEST        := pytest
REPORT_DIR    := test_results
SCRIPTS_DIR   := scripts
TESTS_DIR     := tests

# IP addresses (match docker-compose.yml)
FW1_MGMT_IP     ?= 172.20.0.11
FW2_MGMT_IP     ?= 172.20.0.12
FW3_MGMT_IP     ?= 172.20.0.13
FW1_FRONTEND_IP ?= 172.21.0.11
FW2_FRONTEND_IP ?= 172.21.0.12
FW3_FRONTEND_IP ?= 172.21.0.13
VIRTUAL_IP      ?= 172.20.0.100
SERVER1_IP      ?= 172.22.0.31
SERVER2_IP      ?= 172.22.0.32

# Export all IP vars so pytest and scripts can read them
export FW1_MGMT_IP FW2_MGMT_IP FW3_MGMT_IP
export FW1_FRONTEND_IP FW2_FRONTEND_IP FW3_FRONTEND_IP
export VIRTUAL_IP SERVER1_IP SERVER2_IP
export REPORT_DIR

.PHONY: all up down restart build test test-rules test-failover test-ipv6 \
        test-conntrackd test-traffic monitor report logs status clean help

# Default target
all: help

# ── Docker Compose ──────────────────────────────────────────────────────────

## Build Docker images and start all containers in detached mode
up:
	@echo "→ Building images and starting containers..."
	$(COMPOSE) up -d --build
	@echo "→ Waiting for containers to be healthy..."
	@sleep 5
	$(COMPOSE) ps

## Stop and remove containers (keeps volumes)
down:
	@echo "→ Stopping containers..."
	$(COMPOSE) down

## Restart all containers (rebuild images)
restart: down up

## Build Docker images without starting containers
build:
	$(COMPOSE) build

# ── Testing ─────────────────────────────────────────────────────────────────

## Run the full pytest suite (all test files)
test: $(REPORT_DIR)
	@echo "→ Running full test suite..."
	$(PYTEST) $(TESTS_DIR) \
		--json-report \
		--json-report-file=$(REPORT_DIR)/pytest.json \
		--html=$(REPORT_DIR)/report.html \
		--self-contained-html \
		-v --tb=short
	@echo "→ Report: $(REPORT_DIR)/report.html"

## Run only nftables rules tests (Task 6) — fast, no container restarts
test-rules: $(REPORT_DIR)
	@echo "→ Running nftables rules tests..."
	$(PYTEST) $(TESTS_DIR)/test_nftables_rules.py -v --tb=short

## Run only failover tests (Task 5) — slow, stops/starts containers
test-failover: $(REPORT_DIR)
	@echo "→ Running failover tests (this stops fw nodes — takes ~2 min)..."
	$(PYTEST) $(TESTS_DIR)/test_failover.py -v --tb=short

## Run only IPv6 tests (Task 7)
test-ipv6: $(REPORT_DIR)
	@echo "→ Running IPv6 tests..."
	$(PYTEST) $(TESTS_DIR)/test_ipv6.py -v --tb=short

## Run only conntrackd sync tests
test-conntrackd: $(REPORT_DIR)
	@echo "→ Running conntrackd tests..."
	$(PYTEST) $(TESTS_DIR)/test_conntrackd.py -v --tb=short

## Run scapy traffic generation tests (Task 8) — requires NET_RAW
test-traffic: $(REPORT_DIR)
	@echo "→ Running scapy traffic tests..."
	$(PYTEST) $(TESTS_DIR)/traffic_generator.py -v --tb=short

## Generate traffic from client1 toward fw1 (standalone, no pytest)
traffic-demo:
	@echo "→ Running traffic generator demo from client1..."
	docker exec client1 python3 /tests/traffic_generator.py \
		--target $(FW1_FRONTEND_IP) \
		--mode all \
		--verbose

# ── Monitoring ───────────────────────────────────────────────────────────────

## Start real-time health monitor (Ctrl+C to stop)
monitor: $(REPORT_DIR)
	@echo "→ Starting health monitor (Ctrl+C to stop)..."
	python3 $(SCRIPTS_DIR)/monitor_health.py \
		--interval 5 \
		--output $(REPORT_DIR)/health.json

## Take a single health snapshot and exit
status:
	@echo "→ Cluster status snapshot:"
	@python3 $(SCRIPTS_DIR)/monitor_health.py --once 2>/dev/null || true
	@echo ""
	@echo "→ VIP location:"
	@for c in fw1 fw2 fw3; do \
		result=$$(docker exec $$c ip addr show 2>/dev/null | grep $(VIRTUAL_IP) || true); \
		if [ -n "$$result" ]; then \
			echo "  *** $$c holds VIP $(VIRTUAL_IP) [MASTER] ***"; \
		else \
			echo "  $$c: backup"; \
		fi; \
	done

# ── Reporting ────────────────────────────────────────────────────────────────

## Generate HTML report from last pytest run
report: $(REPORT_DIR)
	@echo "→ Generating report..."
	python3 $(SCRIPTS_DIR)/generate_report.py \
		--pytest-json $(REPORT_DIR)/pytest.json \
		--health-json $(REPORT_DIR)/health.json \
		--output $(REPORT_DIR)/report.html
	@echo "→ Open: $(REPORT_DIR)/report.html"

# ── Logs ────────────────────────────────────────────────────────────────────

## Show live logs from all fw nodes (Ctrl+C to stop)
logs:
	$(COMPOSE) logs -f fw1 fw2 fw3

## Show logs from a specific container: make log C=fw2
log:
	$(COMPOSE) logs -f $(C)

# ── Ansible ─────────────────────────────────────────────────────────────────

## Run Ansible test integration playbook (Task 9)
ansible-test:
	@echo "→ Running Ansible test playbook..."
	ansible-playbook ansible/playbooks/run_tests.yml \
		-i ansible/inventory/hosts.yml \
		-v

# ── Cleanup ──────────────────────────────────────────────────────────────────

## Stop containers and remove all volumes (full reset)
clean:
	@echo "→ Stopping containers and removing volumes..."
	$(COMPOSE) down -v
	@echo "→ Removing test results..."
	rm -rf $(REPORT_DIR)
	@echo "Clean complete."

## Remove built Docker images too (forces full rebuild next time)
clean-images: clean
	docker rmi $$(docker images | grep firewall | awk '{print $$3}') 2>/dev/null || true

# ── Utilities ────────────────────────────────────────────────────────────────

## Create test_results directory if it doesn't exist
$(REPORT_DIR):
	mkdir -p $(REPORT_DIR)

## Show this help message
help:
	@echo ""
	@echo "  HA Firewall — Make targets"
	@echo "  ─────────────────────────────────────────────────"
	@grep -E '^## ' Makefile | sed 's/## /  /' | head -40
	@echo ""
	@echo "  Quick start:"
	@echo "    make up       # start everything"
	@echo "    make status   # check VIP and health"
	@echo "    make test     # run all tests"
	@echo "    make report   # open test_results/report.html"
	@echo ""
