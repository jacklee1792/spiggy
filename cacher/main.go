package main

import (
	"fmt"
	"net/http"
	"time"

	"go.uber.org/zap"
)

func main() {
	fs := &FileStore{BasePath: "data"}
	log, err := zap.NewDevelopment()
	if err != nil {
		fmt.Println(err)
		return
	}
	c := Cacher{
		Store:  fs,
		Client: http.DefaultClient,
		Logger: log,
	}
	c.RepeatCache(time.Second * 20)
}
