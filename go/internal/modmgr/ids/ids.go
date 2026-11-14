// Package ids makes time-sortable unique identifiers (ULID layout: 48-bit
// millisecond time + 80 random bits, Crockford base32, 26 characters).
package ids

import (
	"crypto/rand"
	"sync"
	"time"
)

const alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

var (
	mu   sync.Mutex
	last [16]byte
)

// New returns a new identifier; identifiers made in the same millisecond
// still sort in creation order.
func New() string {
	mu.Lock()
	defer mu.Unlock()
	var b [16]byte
	ms := uint64(time.Now().UnixMilli())
	for i := 5; i >= 0; i-- {
		b[i] = byte(ms)
		ms >>= 8
	}
	if b[0] == last[0] && b[1] == last[1] && b[2] == last[2] && b[3] == last[3] && b[4] == last[4] && b[5] == last[5] {
		b = last
		for i := 15; i >= 6; i-- { // monotonic increment of the random part
			b[i]++
			if b[i] != 0 {
				break
			}
		}
	} else if _, err := rand.Read(b[6:]); err != nil {
		panic(err)
	}
	last = b
	return encode(b)
}

func encode(b [16]byte) string {
	out := make([]byte, 26)
	// 128 bits -> 26 base32 digits (the first digit holds 3 bits)
	var acc uint64
	bits := 0
	i := 25
	for j := 15; j >= 0; j-- {
		acc |= uint64(b[j]) << bits
		bits += 8
		for bits >= 5 && i >= 0 {
			out[i] = alphabet[acc&31]
			acc >>= 5
			bits -= 5
			i--
		}
	}
	for i >= 0 {
		out[i] = alphabet[acc&31]
		acc >>= 5
		i--
	}
	return string(out)
}

// Valid reports whether s looks like an identifier made by New.
func Valid(s string) bool {
	if len(s) != 26 {
		return false
	}
	for i := 0; i < len(s); i++ {
		ok := false
		for j := 0; j < len(alphabet); j++ {
			if s[i] == alphabet[j] {
				ok = true
				break
			}
		}
		if !ok {
			return false
		}
	}
	return true
}
