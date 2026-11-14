// Package secrets protects secret values stored in local_settings.json with
// Windows DPAPI (current user scope). A protected value is stored as
// "dpapi:<base64>"; anything else is a legacy plaintext value.
//
// DPAPI ties the value to the Windows account: on another computer (USB
// drive) it cannot be decrypted and the launcher asks for the secret again.
package secrets

import (
	"encoding/base64"
	"errors"
	"strings"
)

// Prefix marks a protected value.
const Prefix = "dpapi:"

// entropy is mixed into every blob so other DPAPI users cannot decrypt our
// values by accident (it is not a secret).
var entropy = []byte("GameLauncher/local_settings/v1")

// ErrUndecryptable means the value was protected by another account/PC.
var ErrUndecryptable = errors.New("nie można odszyfrować sekretu (inne konto Windows lub inny komputer) – wpisz go ponownie")

// IsProtected reports a "dpapi:" value.
func IsProtected(v string) bool { return strings.HasPrefix(v, Prefix) }

// Protect encrypts a value ("" stays "").
func Protect(plain string) (string, error) {
	if plain == "" || IsProtected(plain) {
		return plain, nil
	}
	blob, err := protect([]byte(plain))
	if err != nil {
		return "", err
	}
	return Prefix + base64.StdEncoding.EncodeToString(blob), nil
}

// Reveal returns the plaintext of a stored value (plaintext values are
// returned as they are).
func Reveal(stored string) (string, error) {
	if !IsProtected(stored) {
		return stored, nil
	}
	blob, err := base64.StdEncoding.DecodeString(strings.TrimPrefix(stored, Prefix))
	if err != nil {
		return "", ErrUndecryptable
	}
	out, err := unprotect(blob)
	if err != nil {
		return "", ErrUndecryptable
	}
	return string(out), nil
}
