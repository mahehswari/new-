# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

FROM golang:1.18

WORKDIR /build

COPY ./go.mod ./go.sum ./

RUN go mod download

RUN ["go", "get", "-u", "github.com/stretchr/testify/assert"]
RUN ["go", "get", "-u", "github.com/stretchr/testify/require"]
RUN ["go", "install", "github.com/rakyll/gotest@latest"]

COPY service/ ./
COPY utils/run-ut.sh ./

CMD ["./run-ut.sh"]
