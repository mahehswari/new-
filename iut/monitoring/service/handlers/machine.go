/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright (c) 2021-2022 Intel Corporation
 */

package handlers

import (
	log "github.com/sirupsen/logrus"
	"github.com/gin-gonic/gin"
	"net/http"
	"monsvc/machines"
)

/* Intermediate structure used to marshall and unmarshall machine describing JSON data */
type machinePayload struct {
	Id     string `json:"id" binding:"required,alphanum"`
	Status string `json:"status" binding:"oneof=init os_start os_fail os_end ek_start ek_fail finish"`
	IpAddr string `json:"ip,omitempty" binding:"isdefault|ip"`
}

/* Intermediate structure used to unmarshall status specifying JSON data */
type statusPayload struct {
	Status string `json:"status" binding:"oneof=init os_start os_fail os_end ek_start ek_fail finish"`
	IpAddr string `json:"ip" binding:"isdefault|ip"`
}

/* Create a machine record from a machine payload */
func (p *machinePayload) toRecord() machines.Record {
	return machines.Record{Id: p.Id, Status: p.Status, IpAddr: p.IpAddr}
}

/* Convert a list of machine records to payload
 *
 * This function is used by request handlers when responding with a list of machines */
func makeMachineListPayload(list machines.List) []machinePayload {
	payload := make([]machinePayload, 0, len(list))

	for _, r := range list {
		payload = append(payload, machinePayload(r))
	}

	return payload
}

/* A structure used to extract machine identifier from a URI */
type specifyMachineUri struct {
	Mid string `uri:"mid" binding:"required,alphanum"`
}


func RetrieveMachines(c *gin.Context) {
	log.Trace("Entry checkpoint")

	records := machines.GetAll()

	c.JSON(http.StatusOK, gin.H{"items": makeMachineListPayload(records)})

	log.Infof("Found %d machine(s)", len(records))
}


func CreateMachine(c *gin.Context) {
	log.Trace("Entry checkpoint")

	var payload machinePayload

	if err := c.ShouldBindJSON(&payload); err != nil {
		log.Infof("New machine payload binding failed: %s", err)

		c.JSON(http.StatusBadRequest, gin.H{"message": "Payload validation error"})
		return
	}

	if _, found := machines.Get(payload.Id); found {
		log.Infof("A machine with specified id (%s) already registered", payload.Id)

		c.JSON(http.StatusBadRequest, gin.H{"message": "Machine already exists"})
		return
	}

	machines.Set(payload.toRecord())

	c.JSON(http.StatusCreated, gin.H{"message": "ok"})

	log.Infof("Registered a new machine (%s)", payload.Id)
}

/* Handle the update machine status request
 *
 * The function will extract the machine id from the request URI (see the specifyMachineUri structure) and the new
 * status from the request payload (see the statusPayload structure) */
func UpdateStatus(c *gin.Context) {
	log.Trace("Entry checkpoint")

	var uri specifyMachineUri

	if err := c.ShouldBindUri(&uri); err != nil {
		log.Infof("Uri binding failed: %s", err)

		c.JSON(http.StatusBadRequest, gin.H{"message": "URI validation error"})
		return
	}

	var payload statusPayload

	if err := c.ShouldBindJSON(&payload); err != nil {
		log.Infof("Machine status binding failed: %s", err)

		c.JSON(http.StatusBadRequest, gin.H{"message": "Payload validation error"})
		return
	}

	record, found := machines.Get(uri.Mid)

	if !found {
		log.Infof("A machine with specified id (%s) was not found", uri.Mid)

		c.JSON(http.StatusNotFound, gin.H{"message": "Unknown machine Id"})
		return
	}

	oldStatus := record.Status
	record.Status = payload.Status
	if len(payload.IpAddr) > 0 {
		record.IpAddr = payload.IpAddr
	}
	machines.Set(record)

	c.JSON(http.StatusOK, gin.H{"message": "ok"})

	log.Infof("Changed machine (%s) status from '%s' to '%s'", uri.Mid, oldStatus, record.Status)
}
