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
SERVER1_IP ?= 172.22.0.31
SERVER2_IP ?= 172.22.0.32

export FW1_MGMT_IP FW2_MGMT_IP FW3_MGMT_IP
export FW1_FRONTEND_IP FW2_FRONTEND_IP FW3_FRONTEND_IP
export VIRTUAL_IP SERVER1_IP SERVER2_IP
export REPORT_DIR

.PHONY: all up down restart build deploy test test-rules test-failover test-ipv6 \
	test-conntrackd test-traffic monitor monitor-dashboard monitor-metrics \
	k8s-rollout k8s-check report logs status clean clean-images help

all: help

up:
	@echo "Building images and starting containers..."
	$(COMPOSE) up -d --build
	$(COMPOSE) ps

down:
	@echo "Stopping containers..."
	$(COMPOSE) down

restart: down up

build:
	$(COMPOSE) build

deploy:
	@echo "Deploying firewall cluster with Ansible..."
	ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbooks/site.yml

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
	$(PYTEST) $(TESTS_DIR)/traffic_generator.py -v --tb=short

monitor: $(REPORT_DIR)
	python3 $(SCRIPTS_DIR)/monitor_health.py \
		--interval 5 \
		--output $(REPORT_DIR)/health.json

monitor-dashboard:
	python3 monitoring/dashboard/app.py

monitor-metrics:
	python3 monitoring/scripts/collect_metrics.py
	python3 monitoring/scripts/view_metrics.py

k8s-rollout:
	bash k8s/rollout.sh

k8s-check:
	python3 scripts/check_deployment.py
	python3 scripts/check_firewall.py
	python3 scripts/check_service.py
	python3 scripts/check_hpa.py

status:
	@python3 $(SCRIPTS_DIR)/monitor_health.py --once 2>/dev/null || true
	@echo ""
	@echo "VIP location:"
	@for c in fw1 fw2 fw3; do \
		result=$$(docker exec $$c ip addr show 2>/dev/null | grep $(VIRTUAL_IP) || true); \
		if [ -n "$$result" ]; then \
			echo "  $$c holds VIP $(VIRTUAL_IP) [MASTER]"; \
		else \
			echo "  $$c: backup"; \
		fi; \
	done

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
	docker rmi $$(docker images | grep firewall | awk '{print $$3}') 2>/dev/null || true

$(REPORT_DIR):
	mkdir -p $(REPORT_DIR)

help:
	@echo ""
	@echo "HA Firewall targets"
	@echo "  make up              build and start containers"
	@echo "  make deploy          run Ansible site.yml"
	@echo "  make status          show health and VIP owner"
	@echo "  make test            run full pytest suite"
	@echo "  make report          generate test report"
	@echo "  make monitor-dashboard  start Flask monitoring dashboard"
	@echo "  make monitor-metrics    collect and print local metrics"
	@echo "  make k8s-rollout        deploy optional Helm/Kubernetes lab"
	@echo "  make k8s-check          check optional Kubernetes resources"
	@echo "  make clean           stop stack and remove volumes"
	@echo ""
