package chatserver_test

import (
	"crypto/sha256"
	"encoding/hex"
	"github.com/snakex21/game-launcher/go/internal/chatserver"

	"golang.org/x/crypto/pbkdf2"
)

func pbkdf2Hex(pw, salt string, iter int) string {
	return hex.EncodeToString(pbkdf2.Key([]byte(pw), []byte(salt), iter, 32, sha256.New))
}

func init() { chatserver.BcryptCost = 4 }
