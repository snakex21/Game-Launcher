// Command mkicon draws the launcher icon (rounded square with a gamepad) and
// writes a multi-size .ico (16, 24, 32, 48, 64, 256 px; PNG entries).
//
//	go run ./tools/mkicon cmd/gamelauncher/icon.ico
package main

import (
	"bytes"
	"encoding/binary"
	"image"
	"image/color"
	"image/png"
	"log"
	"math"
	"os"
)

var (
	bg = color.RGBA{0x5b, 0x8c, 0xff, 0xff}
	fg = color.RGBA{0xff, 0xff, 0xff, 0xff}
)

// coverage samples a shape 4x4 per pixel for anti-aliasing.
func draw(size int) *image.RGBA {
	img := image.NewRGBA(image.Rect(0, 0, size, size))
	s := float64(size)
	inRoundRect := func(x, y, x0, y0, x1, y1, r float64) bool {
		cx := math.Max(x0+r, math.Min(x, x1-r))
		cy := math.Max(y0+r, math.Min(y, y1-r))
		return (x-cx)*(x-cx)+(y-cy)*(y-cy) <= r*r && x >= x0 && x <= x1 && y >= y0 && y <= y1
	}
	inCircle := func(x, y, cx, cy, r float64) bool { return (x-cx)*(x-cx)+(y-cy)*(y-cy) <= r*r }
	shape := func(x, y float64) (float64, color.RGBA) { // 0..1 units
		if !inRoundRect(x, y, 0, 0, 1, 1, 0.22) {
			return 0, bg
		}
		// gamepad body
		pad := inRoundRect(x, y, 0.14, 0.33, 0.86, 0.70, 0.17)
		grip := inCircle(x, y, 0.27, 0.66, 0.13) || inCircle(x, y, 0.73, 0.66, 0.13)
		if pad || grip {
			// d-pad and buttons cut out in the background colour
			dpad := (math.Abs(x-0.31) < 0.035 && math.Abs(y-0.50) < 0.11) || (math.Abs(y-0.50) < 0.035 && math.Abs(x-0.31) < 0.11)
			btn := inCircle(x, y, 0.66, 0.46, 0.045) || inCircle(x, y, 0.75, 0.55, 0.045)
			if dpad || btn {
				return 1, bg
			}
			return 1, fg
		}
		return 1, bg
	}
	const ss = 4
	for py := 0; py < size; py++ {
		for px := 0; px < size; px++ {
			var r, g, b, a float64
			for sy := 0; sy < ss; sy++ {
				for sx := 0; sx < ss; sx++ {
					x := (float64(px) + (float64(sx)+0.5)/ss) / s
					y := (float64(py) + (float64(sy)+0.5)/ss) / s
					cov, c := shape(x, y)
					r += float64(c.R) * cov
					g += float64(c.G) * cov
					b += float64(c.B) * cov
					a += cov
				}
			}
			if a == 0 {
				continue
			}
			img.SetRGBA(px, py, color.RGBA{uint8(r / a), uint8(g / a), uint8(b / a), uint8(255 * a / (ss * ss))})
		}
	}
	return img
}

func main() {
	if len(os.Args) != 2 {
		log.Fatal("usage: mkicon out.ico")
	}
	sizes := []int{16, 24, 32, 48, 64, 256}
	var images [][]byte
	for _, sz := range sizes {
		var b bytes.Buffer
		if err := png.Encode(&b, draw(sz)); err != nil {
			log.Fatal(err)
		}
		images = append(images, b.Bytes())
	}
	var out bytes.Buffer
	binary.Write(&out, binary.LittleEndian, []uint16{0, 1, uint16(len(sizes))})
	offset := 6 + 16*len(sizes)
	for i, sz := range sizes {
		w := uint8(sz)
		if sz >= 256 {
			w = 0
		}
		out.Write([]byte{w, w, 0, 0})
		binary.Write(&out, binary.LittleEndian, []uint16{1, 32})
		binary.Write(&out, binary.LittleEndian, []uint32{uint32(len(images[i])), uint32(offset)})
		offset += len(images[i])
	}
	for _, im := range images {
		out.Write(im)
	}
	if err := os.WriteFile(os.Args[1], out.Bytes(), 0o644); err != nil {
		log.Fatal(err)
	}
}
