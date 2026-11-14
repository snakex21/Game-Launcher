package secrets

import (
	"runtime"
	"strings"
	"testing"
)

func TestRoundTrip(t *testing.T) {
	if runtime.GOOS != "windows" {
		t.Skip()
	}
	p, err := Protect("tajny-klucz ąę")
	if err != nil || !IsProtected(p) || strings.Contains(p, "tajny") {
		t.Fatal(p, err)
	}
	v, err := Reveal(p)
	if err != nil || v != "tajny-klucz ąę" {
		t.Fatal(v, err)
	}
	if again, _ := Protect(p); again != p {
		t.Fatal("double protection")
	}
	if v, _ := Reveal("plain"); v != "plain" {
		t.Fatal("plaintext passthrough")
	}
	if _, err := Reveal(Prefix + "AAAA"); err != ErrUndecryptable {
		t.Fatal("garbage decrypted")
	}
	if e, _ := Protect(""); e != "" {
		t.Fatal("empty")
	}
}
