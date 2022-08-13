package main

import (
	"encoding/json"
	"net/http"
	"time"

	"go.uber.org/zap"
)

type Cacheable interface {
	Key() string
	Timestamp() int
	Body() ([]byte, error)
}

type HTTPDoer interface {
	Do(req *http.Request) (*http.Response, error)
}

type Cacher struct {
	Store  CacheStore
	Client HTTPDoer
	Logger *zap.Logger
}

func (c *Cacher) PutItem(v Cacheable) {
	key := v.Key()
	ok, err := c.Store.HasKey(key)
	if err != nil {
		c.Logger.Info("HasKey operation failed", zap.Error(err))
		return
	}
	if ok {
		c.Logger.Info("Key already exists, skipping PutItem", zap.String("key", key))
		return
	}
	body, err := v.Body()
	if err != nil {
		c.Logger.Info("Failed to get item body", zap.Error(err))
		return
	}
	err = c.Store.Put(key, body)
	if err != nil {
		c.Logger.Info("Failed to put item to store", zap.Error(err))
	}
	c.Logger.Info("Put item to store", zap.String("key", key))
}

func (c *Cacher) RepeatCache(period time.Duration) {
	ch := make(chan Cacheable)
	clk := time.Tick(period)
	for {
		select {
		case item := <-ch:
			c.PutItem(item)
		case <-clk:
			c.Cache(ch)
		}
	}
}

func (c *Cacher) Cache(ch chan<- Cacheable) {
	go c.PutEndedAuctions(ch)
	go c.PutBazaar(ch)
	go c.PutElection(ch)
}

func (c *Cacher) GetEndedAuctions() (*EndedAuctionsResponse, error) {
	url := "https://api.hypixel.net/skyblock/auctions_ended"
	c.Logger.Info("Making request", zap.String("url", url))
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	res, err := c.Client.Do(req)
	if err != nil {
		c.Logger.Info(
			"Bad API response",
			zap.String("url", url),
			zap.Int("status_code", res.StatusCode),
		)
	}
	defer func() {
		_ = res.Body.Close()
	}()
	dc := json.NewDecoder(res.Body)
	var r EndedAuctionsResponse
	if err := dc.Decode(&r); err != nil {
		c.Logger.Info(
			"Failed to marshal API response",
			zap.String("url", url),
		)
		return nil, err
	}
	return &r, nil
}

func (c *Cacher) PutEndedAuctions(ch chan<- Cacheable) {
	r, err := c.GetEndedAuctions()
	if err == nil {
		ch <- r
	}
}

func (c *Cacher) GetBazaar() (*BazaarResponse, error) {
	url := "https://api.hypixel.net/skyblock/bazaar"
	c.Logger.Info("Making request", zap.String("url", url))
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	res, err := c.Client.Do(req)
	if err != nil {
		c.Logger.Info(
			"Bad API response",
			zap.String("url", url),
			zap.Int("status_code", res.StatusCode),
		)
		return nil, err
	}
	defer func() {
		_ = res.Body.Close()
	}()
	dc := json.NewDecoder(res.Body)
	var r BazaarResponse
	if err := dc.Decode(&r); err != nil {
		c.Logger.Info(
			"Failed to marshal API response",
			zap.String("url", url),
		)
		return nil, err
	}
	return &r, nil
}

func (c *Cacher) PutBazaar(ch chan<- Cacheable) {
	r, err := c.GetBazaar()
	if err == nil {
		ch <- r
	}
}

func (c *Cacher) GetElection() (*ElectionResponse, error) {
	url := "https://api.hypixel.net/resources/skyblock/election"
	c.Logger.Info("Making request", zap.String("url", url))
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	res, err := c.Client.Do(req)
	if err != nil {
		c.Logger.Info(
			"Bad API response",
			zap.String("url", url),
			zap.Int("status_code", res.StatusCode),
		)
	}
	defer func() {
		_ = res.Body.Close()
	}()
	dc := json.NewDecoder(res.Body)
	var r ElectionResponse
	if err := dc.Decode(&r); err != nil {
		c.Logger.Info(
			"Failed to marshal API response",
			zap.String("url", url),
		)
		return nil, err
	}
	return &r, nil
}

func (c *Cacher) PutElection(ch chan<- Cacheable) {
	r, err := c.GetElection()
	if err == nil {
		ch <- r
	}
}
