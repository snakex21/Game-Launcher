// Package fsx holds the file operations the mod manager relies on:
// atomic writes, replace-over (also for read-only targets), copies that
// keep attributes, file identity and an inter-process lock.
package fsx

import (
	"encoding/json"
	"errors"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"time"
)

// WriteFileAtomic writes data to path via a temporary file in the same
// folder, flushed before the rename (the old content survives a crash).
func WriteFileAtomic(path string, data []byte, perm os.FileMode) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	tmp := path + ".gl-tmp"
	f, err := os.OpenFile(tmp, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, perm)
	if err != nil {
		return err
	}
	_, err = f.Write(data)
	if err == nil {
		err = f.Sync()
	}
	if cerr := f.Close(); err == nil {
		err = cerr
	}
	if err == nil {
		err = ReplaceFile(tmp, path)
	}
	if err != nil {
		os.Remove(tmp)
	}
	return err
}

// WriteJSONAtomic writes v as indented JSON.
func WriteJSONAtomic(path string, v any) error {
	b, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return err
	}
	return WriteFileAtomic(path, append(b, '\n'), 0o644)
}

// ReadJSON reads a JSON file into v (os.ErrNotExist passes through).
func ReadJSON(path string, v any) error {
	b, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	return json.Unmarshal(b, v)
}

// MakeWritable clears the read-only attribute (missing file: no error).
func MakeWritable(path string) error {
	st, err := os.Lstat(path)
	if err != nil {
		if errors.Is(err, fs.ErrNotExist) {
			return nil
		}
		return err
	}
	if st.Mode().Perm()&0o200 == 0 {
		return os.Chmod(path, st.Mode().Perm()|0o200)
	}
	return nil
}

// IsReadOnly reports whether the file has the read-only attribute.
func IsReadOnly(path string) bool {
	st, err := os.Lstat(path)
	return err == nil && st.Mode().Perm()&0o200 == 0
}

// Remove deletes a file, clearing the read-only attribute if needed.
func Remove(path string) error {
	err := os.Remove(path)
	if err == nil || errors.Is(err, fs.ErrNotExist) {
		return nil
	}
	if werr := MakeWritable(path); werr != nil {
		return err
	}
	if err := os.Remove(path); err != nil && !errors.Is(err, fs.ErrNotExist) {
		return err
	}
	return nil
}

// RemoveAll deletes a tree, clearing read-only attributes on the way.
func RemoveAll(path string) error {
	err := os.RemoveAll(path)
	if err == nil {
		return nil
	}
	_ = filepath.WalkDir(path, func(p string, d fs.DirEntry, err error) error {
		if err == nil && !d.IsDir() {
			_ = MakeWritable(p)
		}
		return nil
	})
	return os.RemoveAll(path)
}

// ReplaceFile renames src over dst (also when dst is read-only).
func ReplaceFile(src, dst string) error {
	err := os.Rename(src, dst)
	if err == nil {
		return nil
	}
	if IsReadOnly(dst) {
		if werr := MakeWritable(dst); werr == nil {
			return os.Rename(src, dst)
		}
	}
	return err
}

// CopyFile copies src to dst (dst must not exist), flushes it and keeps
// the modification time and the read-only attribute of src.
func CopyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	st, err := in.Stat()
	if err != nil {
		return err
	}
	out, err := os.OpenFile(dst, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o644)
	if err != nil {
		return err
	}
	_, err = io.Copy(out, in)
	if err == nil {
		err = out.Sync()
	}
	if cerr := out.Close(); err == nil {
		err = cerr
	}
	if err == nil {
		err = os.Chtimes(dst, st.ModTime(), st.ModTime())
	}
	if err == nil && st.Mode().Perm()&0o200 == 0 {
		err = os.Chmod(dst, 0o444)
	}
	if err != nil {
		os.Remove(dst)
	}
	return err
}

// Exists reports whether path exists (any type).
func Exists(path string) bool {
	_, err := os.Lstat(path)
	return err == nil
}

// SetModTime sets the modification time (clearing read-only temporarily).
func SetModTime(path string, t time.Time) error {
	err := os.Chtimes(path, t, t)
	if err == nil || !IsReadOnly(path) {
		return err
	}
	if err := MakeWritable(path); err != nil {
		return err
	}
	err = os.Chtimes(path, t, t)
	_ = os.Chmod(path, 0o444)
	return err
}
