# Makefile for Market Research Agent

.PHONY: help build run run-prod stop clean logs test

help:
	@echo "Market Research Agent - Available Commands:"
	@echo "  make build       - Build Docker image"
	@echo "  make run         - Run agent once (local)"
	@echo "  make run-prod    - Run with scheduler (production)"
	@echo "  make stop        - Stop all containers"
	@echo "  make clean       - Remove containers and images"
	@echo "  make logs        - View container logs"
	@echo "  make test        - Run agent in test mode"

build:
	docker-compose build

run:
	docker-compose run --rm market-research-agent

run-prod:
	docker-compose -f docker-compose.prod.yml up -d
	@echo "Market Research Agent is running with scheduler!"
	@echo "View logs: make logs"

stop:
	docker-compose -f docker-compose.prod.yml down
	docker-compose down

clean:
	docker-compose -f docker-compose.prod.yml down -v --rmi all
	docker-compose down -v --rmi all

logs:
	docker-compose -f docker-compose.prod.yml logs -f

test:
	@echo "Running test market analysis..."
	docker-compose run --rm market-research-agent python -c "print('Test mode - verifying setup...')"
	docker-compose run --rm market-research-agent python -c "import os; print('Environment check:'); print(f'GROQ_API_KEY: {\"Set\" if os.getenv(\"GROQ_API_KEY\") else \"Not set\"}'); print(f'Email configured: {\"Yes\" if os.getenv(\"TO_EMAIL\") else \"No\"}')"