SHELL := /bin/bash

COMPOSE := docker compose
PYTEST := pytest
REPORT_DIR := test_results
SCRIPTS_DIR := scripts
TESTS_DIR := tests

FW1_MGMT_IP ?= 172.20.0.11
FW2_MGMT_IP ?= 172.20.0.12
FW3_MGMT_IP ?= 172.20.0.13
FW1_FRONTEND_IP ?= 172.21.0.11
FW2_FRONTEND_IP ?= 172.21.0.12
FW3_FRONTEND_IP ?= 172.21.0.13
VIRTUAL_IP ?= 172.20.0.100
FRONTEND_VIP ?= 172.21.0.100
BACKEND_VIP ?= 172.22.0.100
SERVER1_IP ?= 172.22.0.31
SERVER2_IP ?= 172.22.0.32

export FW1_MGMT_IP FW2_MGMT_IP FW3_MGMT_IP
export FW1_FRONTEND_IP FW2_FRONTEND_IP FW3_FRONTEND_IP
export VIRTUAL_IP FRONTEND_VIP BACKEND_VIP SERVER1_IP SERVER2_IP
export REPORT_DIR

.PHONY: all up down restart build deploy test test-rules test-failover test-ipv6 \
	test-conntrackd test-traffic monitor monitor-dashboard monitor-metrics \
	report logs status clean clean-images help

all: help

up:
	@echo "Building images and starting containers..."
	$(COMPOSE) up -d --build
	$(COMPOSE) ps
	@echo "Running Ansible to configure firewalls, keepalived, conntrackd, and routing..."
	$(MAKE) deploy

down:
	@echo "Stopping containers..."
	$(COMPOSE) down

restart: down up

build:
	$(COMPOSE) build

deploy:
	@echo "Deploying firewall cluster with Ansible..."
	ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbooks/site.yml -i ansible/inventory/hosts.yml

test: $(REPORT_DIR)
	$(PYTEST) $(TESTS_DIR) \
		--json-report \
		--json-report-file=$(REPORT_DIR)/pytest.json \
		--html=$(REPORT_DIR)/report.html \
		--self-contained-html \
		-v --tb=short

test-rules: $(REPORT_DIR)
	$(PYTEST) $(TESTS_DIR)/test_nftables_rules.py -v --tb=short

test-failover: $(REPORT_DIR)
	$(PYTEST) $(TESTS_DIR)/test_failover.py -v --tb=short

test-ipv6: $(REPORT_DIR)
	$(PYTEST) $(TESTS_DIR)/test_ipv6.py -v --tb=short

test-conntrackd: $(REPORT_DIR)
	$(PYTEST) $(TESTS_DIR)/test_conntrackd.py -v --tb=short

test-traffic: $(REPORT_DIR)
	docker exec client1 pytest /tests/traffic_generator.py \
		-v --tb=short \
		-k "not http_get_through_firewall"

monitor: $(REPORT_DIR)
	python3 $(SCRIPTS_DIR)/monitor_health.py \
		--interval 5 \
		--output $(REPORT_DIR)/health.json

monitor-dashboard:
	python3 monitoring/dashboard/app.py

monitor-metrics:
	python3 monitoring/scripts/collect_metrics.py --output monitoring/data/metrics.json
	python3 monitoring/scripts/view_metrics.py --input monitoring/data/metrics.json

status: $(REPORT_DIR)
	@python3 $(SCRIPTS_DIR)/monitor_health.py --once --output $(REPORT_DIR)/health.json

report: $(REPORT_DIR)
	python3 $(SCRIPTS_DIR)/generate_report.py \
		--pytest-json $(REPORT_DIR)/pytest.json \
		--health-json $(REPORT_DIR)/health.json \
		--output $(REPORT_DIR)/report.html
	@echo "Report: $(REPORT_DIR)/report.html"

logs:
	$(COMPOSE) logs -f fw1 fw2 fw3

clean:
	$(COMPOSE) down -v
	rm -rf $(REPORT_DIR)

clean-images: clean
	docker rmi $$(docker images | grep $$(basename $$(pwd)) | awk '{print $$3}') 2>/dev/null || true

$(REPORT_DIR):
	mkdir -p $(REPORT_DIR)

help:
	@echo ""
	@echo "HA Firewall targets"
	@echo "  make up                 build, start containers, and deploy via Ansible"
	@echo "  make deploy             run Ansible site.yml only"
	@echo "  make status             single health/VIP snapshot (mgmt/frontend/backend)"
	@echo "  make monitor            continuous health monitor, logs to test_results/health.json"
	@echo "  make test               run full pytest suite"
	@echo "  make report             generate combined HTML test+health report"
	@echo "  make monitor-dashboard  start Flask monitoring dashboard"
	@echo "  make monitor-metrics    collect and print local nftables/conntrack metrics"
	@echo "  make clean              stop stack and remove volumes"
	@echo ""