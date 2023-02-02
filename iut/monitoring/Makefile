# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

# Purpose:
#     Developer convenience tool
#
# Limitations:
#     * Use GNU makefile
#     * Run with sudo if the current user is not in the docker group
#
# Notes:
#     * The run_service target can be parametrized with the LOG_LEVEL variable which will influence the logging
#       threshold of the monitoring service (for the valid values see `monsvc --help` or the service/args.go file).
#       Example:
#       $ make run_service LOG_LEVEL=info

.PHONY: run_service run_ut run_linter

VERSION = 0.1
SERVICE_TAG = iut/monitoring/service:$(VERSION)
UNITTEST_TAG = iut/monitoring/unittest:$(VERSION)
LINTER_TAG = iut/monitoring/linter:$(VERSION)
COVERAGE_OUTPUT_DIR = $(shell pwd)/output
LOG_LEVEL = trace

run_service:
	docker build --tag=$(SERVICE_TAG) .
	docker run -p 8080:8080/tcp -it --rm $(SERVICE_TAG) --log-level=$(LOG_LEVEL)

run_ut:
	docker build -f ut.Dockerfile --tag=$(UNITTEST_TAG) .
	mkdir -p "$(COVERAGE_OUTPUT_DIR)"
	docker run --mount type=bind,source="$(COVERAGE_OUTPUT_DIR)",target=/output -it --rm $(UNITTEST_TAG)

run_linter:
	docker build -f linter.Dockerfile --tag=$(LINTER_TAG) .
	docker run -it --rm $(LINTER_TAG)
