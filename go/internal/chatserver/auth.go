package chatserver

import (
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"strconv"
	"strings"
	"sync"
	"time"

	"golang.org/x/crypto/bcrypt"
	"golang.org/x/crypto/pbkdf2"
	"golang.org/x/crypto/scrypt"
)

// BcryptCost is the bcrypt work factor (tests lower it).
var BcryptCost = 12

// HashPassword returns a bcrypt hash.
func HashPassword(pw string) (string, error) {
	b, err := bcrypt.GenerateFromPassword([]byte(pw), BcryptCost)
	return string(b), err
}

// CheckPassword verifies bcrypt hashes and, for accounts created by the
// Python server, werkzeug "pbkdf2:sha256:N$salt$hex" / "scrypt:n:r:p$salt$hex"
// hashes. legacy=true means the caller should re-hash with bcrypt.
func CheckPassword(hash, pw string) (ok, legacy bool) {
	if strings.HasPrefix(hash, "$2") {
		return bcrypt.CompareHashAndPassword([]byte(hash), []byte(pw)) == nil, false
	}
	parts := strings.SplitN(hash, "$", 3)
	if len(parts) != 3 {
		return false, false
	}
	method, salt, want := parts[0], parts[1], parts[2]
	wantB, err := hex.DecodeString(want)
	if err != nil {
		return false, false
	}
	m := strings.Split(method, ":")
	var got []byte
	switch {
	case m[0] == "pbkdf2" && len(m) >= 2 && m[1] == "sha256":
		iter := 600000
		if len(m) == 3 {
			if n, err := strconv.Atoi(m[2]); err == nil && n > 0 && n <= 10_000_000 {
				iter = n
			}
		}
		got = pbkdf2.Key([]byte(pw), []byte(salt), iter, len(wantB), sha256.New)
	case m[0] == "scrypt" && len(m) == 4:
		n, _ := strconv.Atoi(m[1])
		r, _ := strconv.Atoi(m[2])
		p, _ := strconv.Atoi(m[3])
		if n <= 1 || n > 1<<20 || r <= 0 || r > 32 || p <= 0 || p > 16 {
			return false, false
		}
		got, err = scrypt.Key([]byte(pw), []byte(salt), n, r, p, len(wantB))
		if err != nil {
			return false, false
		}
	default:
		return false, false
	}
	return hmac.Equal(got, wantB), true
}

// NewToken returns a random session token and the hash stored in the DB.
func NewToken() (token, hash string) {
	b := make([]byte, 32)
	_, _ = rand.Read(b)
	token = base64.RawURLEncoding.EncodeToString(b)
	return token, TokenHash(token)
}

// TokenHash is the stored form of a token.
func TokenHash(token string) string {
	h := sha256.Sum256([]byte(token))
	return hex.EncodeToString(h[:])
}

// ------------------------------------------------------------ rate limits

// Limiter is a token bucket per key.
type Limiter struct {
	mu      sync.Mutex
	rate    float64 // tokens per second
	burst   float64
	buckets map[string]*bucket
	now     func() time.Time
}

type bucket struct {
	tokens float64
	last   time.Time
}

// NewLimiter allows `burst` events at once and `perSec` per second after.
func NewLimiter(perSec, burst float64) *Limiter {
	return &Limiter{rate: perSec, burst: burst, buckets: map[string]*bucket{}, now: time.Now}
}

// Allow consumes one token for key.
func (l *Limiter) Allow(key string) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	now := l.now()
	b, ok := l.buckets[key]
	if !ok {
		if len(l.buckets) > 50000 { // bounded memory
			l.buckets = map[string]*bucket{}
		}
		b = &bucket{tokens: l.burst, last: now}
		l.buckets[key] = b
	}
	b.tokens += now.Sub(b.last).Seconds() * l.rate
	if b.tokens > l.burst {
		b.tokens = l.burst
	}
	b.last = now
	if b.tokens < 1 {
		return false
	}
	b.tokens--
	return true
}
