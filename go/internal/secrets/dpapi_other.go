//go:build !windows

package secrets

import "errors"

func protect([]byte) ([]byte, error)   { return nil, errors.New("DPAPI is Windows-only") }
func unprotect([]byte) ([]byte, error) { return nil, errors.New("DPAPI is Windows-only") }
