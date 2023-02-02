/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright (c) 2021-2022 Intel Corporation
 */

package main

import (
	log "github.com/sirupsen/logrus"
	"github.com/gin-gonic/gin"
	"os"
	"monsvc/handlers"
)


func setupRouter() *gin.Engine {
	r := gin.Default()

	//r.DELETE("/machines", deleteMachines) // Stage 1+X
	r.GET("/machines", handlers.RetrieveMachines)
	r.POST("/machines", handlers.CreateMachine)

	r.PUT("/machines/:mid/status", handlers.UpdateStatus)

	return r
}


func main() {
	args, err := parseArgs()

	if err != nil {
		os.Exit(1)
	}

	log.SetReportCaller(true)
	log.SetLevel(args.LogLevel)

	log.Trace("Application entry checkpoint")

	router := setupRouter()

	if err := router.Run(); err != nil {
		log.Fatalf("Failed to run the gin server (%s)", err)
	}
}
