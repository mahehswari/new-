# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

FROM golang:1.18

WORKDIR /build

COPY ./go.mod ./go.sum ./

RUN go mod download

RUN ["go", "get", "-u", "github.com/stretchr/testify/assert"]
RUN ["go", "get", "-u", "github.com/stretchr/testify/require"]
RUN ["go", "install", "github.com/golangci/golangci-lint/cmd/golangci-lint@latest"]

COPY service/ ./

CMD ["golangci-lint", "run"]

