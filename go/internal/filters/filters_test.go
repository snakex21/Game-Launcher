package filters

import (
	"testing"
	"time"

	"github.com/snakex21/game-launcher/go/internal/ojson"
)

func game(t *testing.T, s string) *ojson.Object {
	o, err := ojson.DecodeObject([]byte(s))
	if err != nil {
		t.Fatal(err)
	}
	return o
}

func TestRules(t *testing.T) {
	g := game(t, `{"genres":["RPG","Akcja"],"tags":["sporty","VR"],"rating":8.5,"play_time":7200,"date_added":1700000000,"completion":50,"emulator_name":null}`)
	cases := []struct {
		r    Rule
		want bool
	}{
		{Rule{"name", "zawiera", "witch"}, true},
		{Rule{"name", "zaczyna się od", "the"}, true},
		{Rule{"name", "kończy się na", "3"}, true},
		{Rule{"name", "równa się", "the witcher 3"}, true},
		{Rule{"name", "nie zawiera", "witch"}, false},
		{Rule{"genres", "zawiera", "rpg"}, true},   // case-insensitive list item
		{Rule{"genres", "zawiera", "RP"}, false},   // whole item, not a substring
		{Rule{"tags", "nie zawiera", "VR"}, false}, // the Python bug made list rules always false
		{Rule{"tags", "zawiera", "sporty"}, true},
		{Rule{"rating", ">=", "8"}, true},
		{Rule{"rating", "<", "8,6"}, true},
		{Rule{"play_time", "==", "2"}, true}, // hours
		{Rule{"completion", "!=", "50"}, false},
		{Rule{"date_added", "jest równe", "2023-11-14"}, true},
		{Rule{"date_added", "jest przed", "2024-01-01"}, true},
		{Rule{"date_added", "jest po", "2024-01-01"}, false},
		{Rule{"last_played", "nie jest ustawione", ""}, true},
		{Rule{"emulator_name", "jest ustawione", ""}, false},
		{Rule{"game_type", "jest", "pc"}, true}, // missing type means PC
		{Rule{"game_type", "nie jest", "emulator"}, true},
		{Rule{"unknown", "zawiera", "x"}, false},
	}
	for _, c := range cases {
		if got := Match("The Witcher 3", g, []Rule{c.r}, time.UTC); got != c.want {
			t.Errorf("%+v: got %v, want %v", c.r, got, c.want)
		}
	}
	if !Match("The Witcher 3", g, []Rule{{"genres", "zawiera", "RPG"}, {"rating", ">", "5"}}, time.UTC) {
		t.Error("AND of true rules")
	}
	if Match("The Witcher 3", g, []Rule{{"genres", "zawiera", "RPG"}, {"rating", ">", "9"}}, time.UTC) {
		t.Error("AND with a false rule")
	}
}

// The user's existing filter format (operator strings as stored by Python).
func TestRulesOfStoredFilter(t *testing.T) {
	f := game(t, `{"name":"Nowy Filtr","rules":[{"field":"tags","operator":"zawiera","value":"sporty"}]}`)
	rules := RulesOf(f)
	if len(rules) != 1 || rules[0] != (Rule{"tags", "zawiera", "sporty"}) {
		t.Fatal(rules)
	}
	if !Match("DSJ4", game(t, `{"tags":["Sporty"]}`), rules, time.UTC) {
		t.Fatal("stored filter does not match")
	}
}

func TestValidate(t *testing.T) {
	if Validate(Rule{"rating", ">", "abc"}) == nil || Validate(Rule{"date_added", "jest po", "14.11.2026"}) == nil || Validate(Rule{"tags", ">", "x"}) == nil {
		t.Fatal("invalid rules accepted")
	}
	if err := Validate(Rule{"rating", ">=", "7.5"}); err != nil {
		t.Fatal(err)
	}
}
