package thumbs

import (
	"image"
	"image/color"
	"image/jpeg"
	"image/png"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestGetCreatesAndCaches(t *testing.T) {
	dir := t.TempDir()
	src := filepath.Join(dir, "cover.png")
	img := image.NewRGBA(image.Rect(0, 0, 900, 1200))
	for y := 0; y < 1200; y++ {
		for x := 0; x < 900; x++ {
			img.Set(x, y, color.RGBA{uint8(x), uint8(y), 80, 255})
		}
	}
	f, _ := os.Create(src)
	png.Encode(f, img)
	f.Close()

	c := New(filepath.Join(dir, "cache"))
	p1, err := c.Get(src, 300)
	if err != nil {
		t.Fatal(err)
	}
	tf, _ := os.Open(p1)
	th, err := jpeg.Decode(tf)
	tf.Close()
	if err != nil || th.Bounds().Dx() != 300 || th.Bounds().Dy() != 400 {
		t.Fatalf("%v %v", th.Bounds(), err)
	}
	p2, _ := c.Get(src, 300)
	if p1 != p2 {
		t.Fatal("not cached")
	}
	// replaced cover -> new thumbnail
	later := time.Now().Add(time.Minute)
	os.Chtimes(src, later, later)
	p3, _ := c.Get(src, 300)
	if p3 == p1 {
		t.Fatal("stale thumbnail")
	}
	if _, err := c.Get(filepath.Join(dir, "none.png"), 300); err == nil {
		t.Fatal("missing file accepted")
	}
	os.WriteFile(filepath.Join(dir, "bad.jpg"), []byte("nope"), 0o644)
	if _, err := c.Get(filepath.Join(dir, "bad.jpg"), 300); err == nil {
		t.Fatal("garbage decoded")
	}
}
