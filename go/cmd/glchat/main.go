// Command glchat runs the Game Launcher chat server without the launcher
// (e.g. on a home server). The launcher can also host it itself
// (Czat -> Własny serwer czatu).
package main

import (
	"flag"
	"log"
	"os"
	"os/signal"
	"path/filepath"

	"github.com/snakex21/game-launcher/go/internal/chatserver"
)

func main() {
	addr := flag.String("addr", "127.0.0.1:5000", "listen address (use 0.0.0.0:5000 for LAN)")
	dbPath := flag.String("db", filepath.Join("data", "chat", "chat.db"), "SQLite database (created when missing)")
	uploads := flag.String("uploads", "", "upload folder (default: <db folder>/uploads)")
	flag.Parse()
	if *uploads == "" {
		*uploads = filepath.Join(filepath.Dir(*dbPath), "uploads")
	}
	db, err := chatserver.OpenDB(*dbPath)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	s := chatserver.New(db, *uploads)
	if err := s.Start(*addr); err != nil {
		log.Fatal(err)
	}
	log.Printf("chat server on http://%s (db %s)", s.Addr, *dbPath)
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt)
	<-sig
	s.Stop()
}
