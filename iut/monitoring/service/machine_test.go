/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright (c) 2021-2022 Intel Corporation
 */

package main

import (
	"bytes"
	"encoding/json"
	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"monsvc/machines"
)


type testMachineJson struct {
	Id string     `json:"id"`
	Status string `json:"status"`
}


type testGenericResponseJson struct {
	Message string `json:"message"`
}


/* Execute an HTTP request to be handled by the provided GIN router (which is the test subject) */
func testMakeRequest(router *gin.Engine, method string, url string, body io.Reader) *httptest.ResponseRecorder {
	res := httptest.NewRecorder()
	req := httptest.NewRequest(method, url, body)
	router.ServeHTTP(res, req)
	return res
}

/* Serialize provided payload structure to JSON */
func testMarshalPayload(t *testing.T, payload interface{}) io.Reader {
	data, err := json.Marshal(payload)
	require.Nil(t, err)
	return bytes.NewBuffer(data)
}

func testUnmarshalResponse(t *testing.T, res *httptest.ResponseRecorder, dest interface{}) {
	require.True(t, json.Valid(res.Body.Bytes()))
	err := json.Unmarshal(res.Body.Bytes(), &dest)
	require.Nil(t, err)
}

func testUnmarshalGenericResponse(t *testing.T, res *httptest.ResponseRecorder) testGenericResponseJson {
	data := testGenericResponseJson{}
	testUnmarshalResponse(t, res, &data)
	return data
}


func TestCreateMachineSuccess(t *testing.T) {
	router := setupRouter()

	machines.Clear()

	json := testMachineJson{
		Id:     "abc",
		Status: "init"}

	res := testMakeRequest(router, "POST", "/machines", testMarshalPayload(t, json))

	// Verify the response

	assert.Equal(t, http.StatusCreated, res.Code)

	data := testUnmarshalGenericResponse(t, res)

	assert.Equal(t, "ok", data.Message)

	// Verify the effect on the storage
	assert.Len(t, machines.GetAll(), 1)
	record, found := machines.Get("abc")
	assert.True(t, found)
	assert.Equal(t, "abc", record.Id)
	assert.Equal(t, "init", record.Status)
}
