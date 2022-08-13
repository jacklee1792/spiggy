package main

import (
	"encoding/json"
	"fmt"
)

type EndedAuctionsResponse struct {
	Success     bool              `json:"success"`
	LastUpdated int               `json:"lastUpdated"`
	Auctions    []json.RawMessage `json:"auctions"`
}

func (r *EndedAuctionsResponse) Key() string {
	return fmt.Sprintf("ended-auctions-%v", r.LastUpdated)
}

func (r *EndedAuctionsResponse) Timestamp() int {
	return r.LastUpdated
}

func (r *EndedAuctionsResponse) Body() ([]byte, error) {
	return json.Marshal(r)
}

type BazaarResponse struct {
	Success     bool            `json:"success"`
	LastUpdated int             `json:"lastUpdated"`
	Products    json.RawMessage `json:"products"`
}

func (r *BazaarResponse) Key() string {
	return fmt.Sprintf("bazaar-%v", r.LastUpdated)
}

func (r *BazaarResponse) Timestamp() int {
	return r.LastUpdated
}

func (r *BazaarResponse) Body() ([]byte, error) {
	return json.Marshal(r)
}

type ElectionResponse struct {
	Success     bool            `json:"success"`
	LastUpdated int             `json:"lastUpdated"`
	Mayor       json.RawMessage `json:"mayor"`
	Current     json.RawMessage `json:"current"`
}

func (r *ElectionResponse) Key() string {
	return fmt.Sprintf("election-%v", r.LastUpdated)
}

func (r *ElectionResponse) Timestamp() int {
	return r.LastUpdated
}

func (r *ElectionResponse) Body() ([]byte, error) {
	return json.Marshal(r)
}
