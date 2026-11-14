//go:build !windows

package fsx

import (
	"fmt"
	"os"
	"syscall"
)

// FreeSpace returns the bytes available on the volume of dir.
func FreeSpace(dir string) (int64, error) {
	var st syscall.Statfs_t
	if err := syscall.Statfs(dir, &st); err != nil {
		return 0, err
	}
	return int64(st.Bavail) * int64(st.Bsize), nil
}

// FileID identifies the file data (device + inode).
func FileID(path string) (string, error) {
	st, err := os.Lstat(path)
	if err != nil {
		return "", err
	}
	s, ok := st.Sys().(*syscall.Stat_t)
	if !ok {
		return "", fmt.Errorf("brak identyfikatora pliku")
	}
	return fmt.Sprintf("%x:%x", s.Dev, s.Ino), nil
}

// Lock is an exclusive inter-process lock on a file.
type Lock struct{ f *os.File }

// TryLock takes the lock or fails at once.
func TryLock(path string) (*Lock, error) {
	f, err := os.OpenFile(path, os.O_RDWR|os.O_CREATE, 0o644)
	if err != nil {
		return nil, err
	}
	if err := syscall.Flock(int(f.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); err != nil {
		f.Close()
		return nil, fmt.Errorf("inna operacja na tej grze jest w toku (%w)", err)
	}
	return &Lock{f: f}, nil
}

// Unlock releases the lock.
func (l *Lock) Unlock() {
	if l == nil || l.f == nil {
		return
	}
	l.f.Close()
	l.f = nil
}
