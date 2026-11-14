package conflict

import (
	"testing"

	"github.com/snakex21/game-launcher/go/internal/modmgr/gamedef"
)

func f(rel, sha string) File {
	return File{Target: gamedef.Location{Root: gamedef.RootGame, Rel: rel}, Rel: rel, SHA256: sha}
}

func TestWinners(t *testing.T) {
	mods := []Mod{
		{ID: "A", Name: "A", Enabled: true, Files: []File{f("Data/x.dds", "1"), f("Data/same.txt", "s"), f("data/CASE.txt", "a")}},
		{ID: "B", Name: "B", Enabled: true, Files: []File{f("Data/x.dds", "2"), f("Data/same.txt", "s"), f("Data/case.txt", "b")}},
		{ID: "C", Name: "C", Enabled: false, Files: []File{f("Data/x.dds", "3")}},
	}
	idx := Build(mods, nil)
	if w := idx.Entries["game:data/x.dds"].Winner; w != "B" {
		t.Fatal("later enabled mod must win, got", w)
	}
	if !idx.Entries["game:data/same.txt"].Identical {
		t.Fatal("identical not detected")
	}
	if idx.Entries["game:data/case.txt"].Winner != "B" || len(idx.Entries["game:data/case.txt"].Providers) != 2 {
		t.Fatal("case-insensitive keys")
	}
	s := idx.Summaries()
	if s["A"].Loses != 2 || s["B"].Wins != 2 || s["A"].Identical != 1 || s["C"] != (Summary{}) {
		t.Fatal(s)
	}
	// rule for A; rule for a disabled mod is ignored
	idx = Build(mods, map[string]string{"game:data/x.dds": "A", "game:data/case.txt": "C"})
	if e := idx.Entries["game:data/x.dds"]; e.Winner != "A" || e.Rule != "override" || e.WinnerFile().SHA256 != "1" {
		t.Fatal(e)
	}
	if idx.Entries["game:data/case.txt"].Winner != "B" {
		t.Fatal("rule for disabled mod applied")
	}
	if len(idx.ForMod("A")) != 3 || len(idx.Conflicts()) != 3 {
		t.Fatal(idx.ForMod("A"))
	}
	clean := CleanOverrides(mods[:2], map[string]string{"game:data/x.dds": "A", "game:data/gone.txt": "A", "game:data/case.txt": "C"})
	if len(clean) != 1 {
		t.Fatal(clean)
	}
}
