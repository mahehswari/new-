# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2021-2022 Intel Corporation

FROM golang:1.18 AS build

WORKDIR /build

COPY ./go.mod ./go.sum ./

RUN go mod download

COPY service/ ./

RUN CGO_ENABLED=0 go build

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

FROM alpine:3.15.4

WORKDIR /app

COPY --from=build /build/monsvc ./monsvc

EXPOSE 8080/tcp

ENTRYPOINT ["/app/monsvc"]
