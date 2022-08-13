package main

import (
	"errors"
	"io"
	"os"
	"path"
)

type CacheStore interface {
	Get(key string) (io.ReadCloser, error)
	Put(key string, v []byte) error
	HasKey(key string) (bool, error)
}

type FileStore struct {
	BasePath string
}

func (s *FileStore) Get(key string) (io.ReadCloser, error) {
	fp := path.Join(s.BasePath, key)
	return os.Open(fp)
}

func (s *FileStore) Put(key string, v []byte) error {
	fp := path.Join(s.BasePath, key)
	return os.WriteFile(fp, v, 0666)
}

func (s *FileStore) HasKey(key string) (bool, error) {
	fp := path.Join(s.BasePath, key)
	_, err := os.Stat(fp)
	if err == nil {
		return true, nil
	}
	if errors.Is(err, os.ErrNotExist) {
		return false, nil
	}
	return false, err
}
