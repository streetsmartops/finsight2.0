# FinSight — developer + demo shortcuts.  `make help`
PORT ?= 8000
export PYTHONPATH := $(CURDIR)/src

.PHONY: help install test run demo demo-offline demo-docker stop smoke docker video

help:          ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-13s\033[0m %s\n", $$1, $$2}'

install:       ## install runtime + test deps into the current env
	pip install -r requirements.txt pytest

test:          ## run the 14-test suite (engines + grounding contract)
	python -m pytest tests -v

run:           ## run the cockpit in the foreground with reload
	uvicorn api.main:app --reload --port $(PORT)

demo:          ## one-command live demo (venv, tests, server, smoke test)
	./demo/demo.sh

demo-offline:  ## live demo forced into template mode (no network / key needed)
	./demo/demo.sh --offline

demo-docker:   ## live demo inside docker compose
	./demo/demo.sh --docker

stop:          ## stop the background demo server / container
	./demo/demo.sh --stop

smoke:         ## pre-flight check against a running server
	./demo/smoke_test.sh http://localhost:$(PORT)

docker:        ## build the container image
	docker build -t finsight:demo .

video:         ## re-record the captioned demo video (server must be running)
	python demo/video/record_demo.py --url http://localhost:$(PORT)
