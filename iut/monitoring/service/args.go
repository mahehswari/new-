/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright (c) 2021-2022 Intel Corporation
 */

package main

import (
	flags "github.com/jessevdk/go-flags"
	log "github.com/sirupsen/logrus"
	"os"
)


type Args struct {
	LogLevel log.Level
}


// The function will end the application execution when the --help option is handled or argument parsing error occurs
func parseArgs() (Args, error) {
	// The go-flags specification and raw output destination
	var raw struct {
		// LogLevel is used to set the logger threshold
		LogLevel string `long:"log-level" choice:"trace" choice:"debug" choice:"info" choice:"warn" choice:"error" choice:"fatal" choice:"panic" default:"info" description:"Logging threshold"`
	}

	
	if _, err := flags.Parse(&raw); err != nil {
		if flags.WroteHelp(err) {
			// The go-flags package has just wrote the command help
			os.Exit(0)
		}

		// The go-flags package takes care for error printing, so the command may simply end its execution
		os.Exit(1)
	}

	// Convert the log level argument from string to logrus.Level
	level, err := log.ParseLevel(raw.LogLevel)
	if err != nil {
		log.Debugf("Failed to parse the raw log level (%s)", raw.LogLevel)
		return Args{}, err
	}

	// Return the final args structure:
	return Args{
		LogLevel: level,
	}, nil
}
