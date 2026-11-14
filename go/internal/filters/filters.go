// Package filters evaluates the saved advanced filters
// (config.json: saved_filters[name] = {name, rules: [{field, operator, value}]}).
// Rules are combined with AND. Field names and the Polish operator strings
// are the ones the Python launcher stores, so existing filters keep working.
package filters

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/snakex21/game-launcher/go/internal/ojson"
)

// Field kinds.
const (
	Text   = "text"
	List   = "list"
	Number = "number"
	Date   = "date"
	Choice = "choice"
)

// Field describes a filterable game field.
type Field struct {
	Key   string `json:"key"`
	Label string `json:"label"`
	Kind  string `json:"kind"`
}

// Fields in the order shown in the editor.
var Fields = []Field{
	{"name", "Nazwa gry", Text},
	{"genres", "Gatunek", List},
	{"tags", "Tag", List},
	{"rating", "Ocena", Number},
	{"play_time", "Czas gry (godz.)", Number},
	{"date_added", "Data dodania", Date},
	{"last_played", "Data ost. gry", Date},
	{"game_type", "Typ gry", Choice},
	{"emulator_name", "Emulator", Choice},
	{"completion", "Ukończenie (%)", Number},
}

// Operators per kind.
var Operators = map[string][]string{
	Text:   {"zawiera", "nie zawiera", "równa się", "zaczyna się od", "kończy się na", "jest ustawione", "nie jest ustawione"},
	List:   {"zawiera", "nie zawiera", "jest ustawione", "nie jest ustawione"},
	Number: {"==", "!=", ">", "<", ">=", "<=", "jest ustawione", "nie jest ustawione"},
	Date:   {"jest równe", "jest przed", "jest po", "jest ustawione", "nie jest ustawione"},
	Choice: {"jest", "nie jest", "jest ustawione", "nie jest ustawione"},
}

func fieldKind(key string) string {
	for _, f := range Fields {
		if f.Key == key {
			return f.Kind
		}
	}
	return ""
}

// Rule is one condition.
type Rule struct {
	Field    string `json:"field"`
	Operator string `json:"operator"`
	Value    string `json:"value"`
}

// RulesOf reads the rules of a saved filter object.
func RulesOf(filter *ojson.Object) []Rule {
	var out []Rule
	for _, r := range filter.Arr("rules") {
		ro, ok := r.(*ojson.Object)
		if !ok {
			continue
		}
		out = append(out, Rule{Field: ro.Str("field"), Operator: ro.Str("operator"), Value: valueString(ro.Get("value"))})
	}
	return out
}

func valueString(v any) string {
	switch x := v.(type) {
	case nil:
		return ""
	case string:
		return x
	default:
		return string(ojson.MarshalCompact(x))
	}
}

// Validate checks a rule against the field/operator tables.
func Validate(r Rule) error {
	kind := fieldKind(r.Field)
	if kind == "" {
		return fmt.Errorf("nieznane pole „%s”", r.Field)
	}
	for _, op := range Operators[kind] {
		if op == r.Operator {
			if kind == Number && !isPresenceOp(op) {
				if _, err := strconv.ParseFloat(strings.ReplaceAll(strings.TrimSpace(r.Value), ",", "."), 64); err != nil {
					return fmt.Errorf("wartość „%s” nie jest liczbą", r.Value)
				}
			}
			if kind == Date && !isPresenceOp(op) {
				if _, err := time.Parse("2006-01-02", strings.TrimSpace(r.Value)); err != nil {
					return fmt.Errorf("data musi mieć format RRRR-MM-DD")
				}
			}
			return nil
		}
	}
	return fmt.Errorf("operator „%s” nie pasuje do pola „%s”", r.Operator, r.Field)
}

func isPresenceOp(op string) bool { return op == "jest ustawione" || op == "nie jest ustawione" }

// Match reports whether a game passes all rules. Unknown fields/operators
// fail the rule (never silently match everything).
func Match(name string, game *ojson.Object, rules []Rule, loc *time.Location) bool {
	for _, r := range rules {
		if !matchRule(name, game, r, loc) {
			return false
		}
	}
	return true
}

func matchRule(name string, g *ojson.Object, r Rule, loc *time.Location) bool {
	kind := fieldKind(r.Field)
	val := strings.TrimSpace(r.Value)
	lv := strings.ToLower(val)
	var raw any
	if r.Field == "name" {
		raw = name
	} else {
		raw = g.Get(r.Field)
	}
	if r.Field == "game_type" && (raw == nil || raw == "") {
		raw = "pc"
	}
	set := isSet(raw)
	switch r.Operator {
	case "jest ustawione":
		return set
	case "nie jest ustawione":
		return !set
	}
	switch kind {
	case Text:
		s := strings.ToLower(fmt.Sprint(stringOr(raw)))
		switch r.Operator {
		case "zawiera":
			return strings.Contains(s, lv)
		case "nie zawiera":
			return !strings.Contains(s, lv)
		case "równa się":
			return s == lv
		case "zaczyna się od":
			return strings.HasPrefix(s, lv)
		case "kończy się na":
			return strings.HasSuffix(s, lv)
		}
	case List:
		has := false
		if arr, ok := raw.([]any); ok {
			for _, it := range arr {
				if s, ok := it.(string); ok && strings.EqualFold(strings.TrimSpace(s), val) {
					has = true
					break
				}
			}
		}
		switch r.Operator {
		case "zawiera":
			return has
		case "nie zawiera":
			return !has
		}
	case Number:
		f, ok := ojson.ToFloat(raw)
		if !ok {
			return false
		}
		if r.Field == "play_time" {
			f /= 3600
		}
		want, err := strconv.ParseFloat(strings.ReplaceAll(val, ",", "."), 64)
		if err != nil {
			return false
		}
		switch r.Operator {
		case "==":
			return f == want
		case "!=":
			return f != want
		case ">":
			return f > want
		case "<":
			return f < want
		case ">=":
			return f >= want
		case "<=":
			return f <= want
		}
	case Date:
		f, ok := ojson.ToFloat(raw)
		if !ok || f <= 0 {
			return false
		}
		d := time.Unix(int64(f), 0).In(loc).Format("2006-01-02")
		switch r.Operator {
		case "jest równe":
			return d == val
		case "jest przed":
			return d < val
		case "jest po":
			return d > val
		}
	case Choice:
		s := strings.ToLower(fmt.Sprint(stringOr(raw)))
		switch r.Operator {
		case "jest":
			return s == lv
		case "nie jest":
			return s != lv
		}
	}
	return false
}

func stringOr(v any) any {
	if v == nil {
		return ""
	}
	return v
}

func isSet(v any) bool {
	switch x := v.(type) {
	case nil:
		return false
	case string:
		return strings.TrimSpace(x) != ""
	case []any:
		return len(x) > 0
	}
	return true
}
