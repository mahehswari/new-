/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright (c) 2021-2022 Intel Corporation
 */

package machines

import (
	log "github.com/sirupsen/logrus"
)

// Possible status codes
const (
	sInitial           = "init" //nolint:unused,deadcode,varcheck
	sInstallInProgress = "os_start" //nolint:unused,deadcode,varcheck
	sInstallFailed     = "os_fail" //nolint:unused,deadcode,varcheck
	sInstallSuccess    = "os_end" //nolint:unused,deadcode,varcheck
	sDeployInProgress  = "ek_start" //nolint:unused,deadcode,varcheck
	sDeployFailed      = "ek_fail" //nolint:unused,deadcode,varcheck
	sDeploySuccess     = "ek_end" //nolint:unused,deadcode,varcheck
)


/* The machine record. Currently it is the same as the machinePayload but the assumption is that it will store extra
 * data like the machine IP, status change timestamp, or even change history */
type Record struct {
	Id     string
	Status string
	IpAddr string
}


type List []Record

var machines = map[string]Record{}


func Clear() {
	machines = map[string]Record{}
}


func Set(mr Record) {
	machines[mr.Id] = mr
}


/* Retrieve a machine record by id
 * Returns:
 * * Machine record structure (not initialized if the record was not found)
 * * Success flag (true if the record was found and false otherwise) */
func Get(mid string) (Record, bool) {
	log.Debugf("Retrieving machine record (%s)", mid)

	machine, found := machines[mid]

	if !found {
		log.Debugf("Machine record (%s) not found", mid)

		return machine, false
	}

	return machine, true
}


/* Return the list of machines
 * @todo: May later be extended to support pagination */
func GetAll() (List) {
	log.Debugf("Retrieving list of machine records")

	list := make(List, 0, len(machines))

	for _, r := range machines {
		list = append(list, r)
	}

	return list
}

