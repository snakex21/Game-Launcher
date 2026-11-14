//go:build !windows

package procwatch

import "errors"

// List is only implemented on Windows.
func List() ([]Process, error) { return nil, errors.New("not supported") }

// Terminate is only implemented on Windows.
func Terminate(uint32) error { return errors.New("not supported") }
