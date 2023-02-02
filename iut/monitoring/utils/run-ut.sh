#!/usr/bin/env bash

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

# Purpose:
#     Execute the monitoring service unit tests and generate a coverage report
#
# Limitations:
#     This script is supposed to be executed from within the ut.Dockerfile container

gotest . -v -cover -coverprofile cover.out
go tool cover -html=cover.out -o /output/cover.html
