// Package thumbs makes small cached JPEG thumbnails of covers, so the
// library grid never decodes multi-megabyte originals (covers in images/
// are often 1–3 MB each).
package thumbs

import (
	"crypto/sha1"
	"encoding/hex"
	"errors"
	"fmt"
	"image"
	_ "image/gif"
	"image/jpeg"
	_ "image/png"
	"os"
	"path/filepath"
	"runtime/debug"
	"sync"
	"sync/atomic"

	"golang.org/x/image/draw"
	_ "golang.org/x/image/webp"
)

// Cache creates thumbnails on demand.
type Cache struct {
	Dir     string
	mu      sync.Mutex
	inf     map[string]*sync.Mutex // per-key locks (no duplicate work)
	sem     chan struct{}          // bounds concurrent decodes (memory)
	pending atomic.Int32
}

// New returns a cache in dir.
func New(dir string) *Cache {
	return &Cache{Dir: dir, inf: map[string]*sync.Mutex{}, sem: make(chan struct{}, 2)}
}

func (c *Cache) lock(key string) func() {
	c.mu.Lock()
	m, ok := c.inf[key]
	if !ok {
		m = &sync.Mutex{}
		c.inf[key] = m
	}
	c.mu.Unlock()
	m.Lock()
	return m.Unlock
}

// Get returns the path of a thumbnail of src at most width px wide,
// creating it when needed. The key includes size and mtime, so a replaced
// cover gets a new thumbnail.
func (c *Cache) Get(src string, width int) (string, error) {
	if width < 32 || width > 1200 {
		return "", errors.New("invalid width")
	}
	st, err := os.Stat(src)
	if err != nil || st.IsDir() {
		return "", fmt.Errorf("no image: %s", src)
	}
	h := sha1.Sum([]byte(fmt.Sprintf("%s|%d|%d|%d", src, st.Size(), st.ModTime().UnixNano(), width)))
	key := hex.EncodeToString(h[:])
	out := filepath.Join(c.Dir, key[:2], key+".jpg")
	if _, err := os.Stat(out); err == nil {
		return out, nil
	}
	unlock := c.lock(key)
	defer unlock()
	if _, err := os.Stat(out); err == nil {
		return out, nil
	}
	c.pending.Add(1)
	c.sem <- struct{}{}
	err = Make(src, out, width)
	<-c.sem
	if c.pending.Add(-1) == 0 {
		// Decoding multi-megabyte covers leaves big buffers behind; give
		// them back to the OS once the burst of first-run thumbnails ends.
		go debug.FreeOSMemory()
	}
	if err != nil {
		return "", err
	}
	return out, nil
}

// Make writes a thumbnail of src to dst.
func Make(src, dst string, width int) error {
	f, err := os.Open(src)
	if err != nil {
		return err
	}
	defer f.Close()
	img, _, err := image.Decode(f)
	if err != nil {
		return fmt.Errorf("decode %s: %w", filepath.Base(src), err)
	}
	b := img.Bounds()
	if b.Dx() <= 0 || b.Dy() <= 0 {
		return errors.New("empty image")
	}
	w := width
	if b.Dx() < w {
		w = b.Dx()
	}
	hgt := b.Dy() * w / b.Dx()
	if hgt < 1 {
		hgt = 1
	}
	dstImg := image.NewRGBA(image.Rect(0, 0, w, hgt))
	// BiLinear widens its kernel when shrinking, so big downscales stay smooth.
	draw.BiLinear.Scale(dstImg, dstImg.Bounds(), img, b, draw.Src, nil)
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return err
	}
	tmp, err := os.CreateTemp(filepath.Dir(dst), ".thumb-*")
	if err != nil {
		return err
	}
	if err := jpeg.Encode(tmp, dstImg, &jpeg.Options{Quality: 84}); err != nil {
		tmp.Close()
		os.Remove(tmp.Name())
		return err
	}
	tmp.Close()
	if err := os.Rename(tmp.Name(), dst); err != nil {
		os.Remove(tmp.Name())
		return err
	}
	return nil
}
