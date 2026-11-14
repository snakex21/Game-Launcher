// Package ojson is an order-preserving JSON tree used for the launcher's
// existing data files (config.json, local_settings.json).
//
// The Python launcher writes those files with
// json.dump(data, f, indent=4, ensure_ascii=False). To read them unchanged
// and write them back in a form that the Python version (and a diff) still
// recognises, this package:
//   - keeps the key order of every object (new keys are appended, like a
//     Python dict),
//   - keeps numbers as their original text (json.Number), so floats such as
//     play_time = 1157.0904660224915 survive a round trip bit-for-bit,
//   - keeps every unknown key, so features not ported yet lose no data,
//   - encodes exactly like Python's json module with indent=4 and
//     ensure_ascii=False.
//
// Values are: nil, bool, json.Number, string, []any, *Object.
package ojson

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
	"strconv"
	"strings"
	"unicode/utf8"
)

// Object is a JSON object that remembers key order.
type Object struct {
	keys []string
	m    map[string]any
}

// NewObject returns an empty object.
func NewObject() *Object { return &Object{m: map[string]any{}} }

// Len is the number of keys.
func (o *Object) Len() int {
	if o == nil {
		return 0
	}
	return len(o.keys)
}

// Keys returns the keys in order (a copy).
func (o *Object) Keys() []string {
	if o == nil {
		return nil
	}
	return append([]string(nil), o.keys...)
}

// Has reports whether key exists.
func (o *Object) Has(key string) bool {
	if o == nil {
		return false
	}
	_, ok := o.m[key]
	return ok
}

// Get returns the value of key (nil when missing).
func (o *Object) Get(key string) any {
	if o == nil {
		return nil
	}
	return o.m[key]
}

// Lookup returns the value and whether it exists.
func (o *Object) Lookup(key string) (any, bool) {
	if o == nil {
		return nil, false
	}
	v, ok := o.m[key]
	return v, ok
}

// Set sets key; a new key is appended at the end (Python dict semantics).
func (o *Object) Set(key string, v any) {
	if _, ok := o.m[key]; !ok {
		o.keys = append(o.keys, key)
	}
	o.m[key] = Normalize(v)
}

// SetDefault sets key only when it is missing and returns the stored value
// (Python dict.setdefault).
func (o *Object) SetDefault(key string, v any) any {
	if cur, ok := o.m[key]; ok {
		return cur
	}
	o.Set(key, v)
	return o.m[key]
}

// Delete removes key.
func (o *Object) Delete(key string) {
	if _, ok := o.m[key]; !ok {
		return
	}
	delete(o.m, key)
	for i, k := range o.keys {
		if k == key {
			o.keys = append(o.keys[:i], o.keys[i+1:]...)
			break
		}
	}
}

// Rename changes a key in place, keeping its position. It fails when the
// new key already exists.
func (o *Object) Rename(oldKey, newKey string) error {
	if oldKey == newKey {
		return nil
	}
	if _, ok := o.m[newKey]; ok {
		return fmt.Errorf("key %q already exists", newKey)
	}
	v, ok := o.m[oldKey]
	if !ok {
		return fmt.Errorf("key %q not found", oldKey)
	}
	for i, k := range o.keys {
		if k == oldKey {
			o.keys[i] = newKey
		}
	}
	delete(o.m, oldKey)
	o.m[newKey] = v
	return nil
}

// Obj returns key as an object or nil.
func (o *Object) Obj(key string) *Object {
	v, _ := o.Get(key).(*Object)
	return v
}

// EnsureObj returns key as an object, creating (or replacing a non-object
// value with) an empty one.
func (o *Object) EnsureObj(key string) *Object {
	if v, ok := o.Get(key).(*Object); ok {
		return v
	}
	n := NewObject()
	o.Set(key, n)
	return n
}

// Arr returns key as an array or nil.
func (o *Object) Arr(key string) []any {
	v, _ := o.Get(key).([]any)
	return v
}

// Str returns key as a string ("" when missing or not a string).
func (o *Object) Str(key string) string {
	v, _ := o.Get(key).(string)
	return v
}

// Bool returns key as a bool (def when missing or not a bool).
func (o *Object) Bool(key string, def bool) bool {
	if v, ok := o.Get(key).(bool); ok {
		return v
	}
	return def
}

// Float returns key as a number (def when missing / not a number).
func (o *Object) Float(key string, def float64) float64 {
	if f, ok := ToFloat(o.Get(key)); ok {
		return f
	}
	return def
}

// Int returns key as an integer (def when missing / not a number).
func (o *Object) Int(key string, def int64) int64 {
	if f, ok := ToFloat(o.Get(key)); ok && !math.IsInf(f, 0) && !math.IsNaN(f) {
		return int64(f)
	}
	return def
}

// Strings returns key as a []string (non-string items are skipped).
func (o *Object) Strings(key string) []string {
	arr := o.Arr(key)
	out := make([]string, 0, len(arr))
	for _, v := range arr {
		if s, ok := v.(string); ok {
			out = append(out, s)
		}
	}
	return out
}

// Clone deep-copies the object.
func (o *Object) Clone() *Object {
	if o == nil {
		return nil
	}
	c := &Object{keys: append([]string(nil), o.keys...), m: make(map[string]any, len(o.m))}
	for k, v := range o.m {
		c.m[k] = CloneValue(v)
	}
	return c
}

// CloneValue deep-copies any tree value.
func CloneValue(v any) any {
	switch x := v.(type) {
	case *Object:
		return x.Clone()
	case []any:
		out := make([]any, len(x))
		for i, e := range x {
			out[i] = CloneValue(e)
		}
		return out
	default:
		return v
	}
}

// ToFloat converts a numeric tree value.
func ToFloat(v any) (float64, bool) {
	switch x := v.(type) {
	case json.Number:
		f, err := x.Float64()
		return f, err == nil
	case float64:
		return x, true
	case int:
		return float64(x), true
	case int64:
		return float64(x), true
	}
	return 0, false
}

// Float makes a JSON number from a float, formatted like Python's repr()
// (so 0 becomes "0.0", 1e16 becomes "1e+16").
func Float(f float64) json.Number { return json.Number(PyFloat(f)) }

// Int makes a JSON integer.
func Int(n int64) json.Number { return json.Number(strconv.FormatInt(n, 10)) }

// PyFloat formats f like Python's float repr.
func PyFloat(f float64) string {
	switch {
	case math.IsNaN(f):
		return "NaN"
	case math.IsInf(f, 1):
		return "Infinity"
	case math.IsInf(f, -1):
		return "-Infinity"
	}
	e := strconv.FormatFloat(f, 'e', -1, 64)
	i := strings.LastIndexByte(e, 'e')
	exp, _ := strconv.Atoi(e[i+1:])
	if exp >= -4 && exp < 16 {
		s := strconv.FormatFloat(f, 'f', -1, 64)
		if !strings.ContainsAny(s, ".") {
			s += ".0"
		}
		return s
	}
	// Python: mantissa without trailing ".0", exponent with sign and >= 2 digits.
	mant, ex := e[:i], e[i+1:]
	sign := ex[0]
	digits := strings.TrimLeft(ex[1:], "0")
	if len(digits) < 2 {
		digits = strings.Repeat("0", 2-len(digits)) + digits
	}
	return mant + "e" + string(sign) + digits
}

// Normalize converts Go values produced by encoding/json (float64,
// map[string]any) or by the app (int, []string ...) to tree values.
func Normalize(v any) any {
	switch x := v.(type) {
	case nil, bool, string, json.Number, *Object:
		return v
	case float64:
		if x == math.Trunc(x) && math.Abs(x) < 1e15 {
			// Values that are integral in JS land: keep floats as floats only
			// when the caller asks for it explicitly with Float().
			return Int(int64(x))
		}
		return Float(x)
	case float32:
		return Normalize(float64(x))
	case int:
		return Int(int64(x))
	case int64:
		return Int(x)
	case int32:
		return Int(int64(x))
	case uint32:
		return Int(int64(x))
	case []any:
		out := make([]any, len(x))
		for i, e := range x {
			out[i] = Normalize(e)
		}
		return out
	case []string:
		out := make([]any, len(x))
		for i, e := range x {
			out[i] = e
		}
		return out
	case map[string]any:
		// Unordered input (from the UI): sort keys for determinism.
		o := NewObject()
		for _, k := range sortedKeys(x) {
			o.Set(k, x[k])
		}
		return o
	}
	return fmt.Sprint(v)
}

func sortedKeys(m map[string]any) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	// small maps: insertion sort keeps the dependency list empty
	for i := 1; i < len(keys); i++ {
		for j := i; j > 0 && keys[j] < keys[j-1]; j-- {
			keys[j], keys[j-1] = keys[j-1], keys[j]
		}
	}
	return keys
}

// ---------------------------------------------------------------- decoding

// Decode parses one JSON value from data.
func Decode(data []byte) (any, error) {
	// Python's json module accepts a UTF-8 BOM only via utf-8-sig; be lenient.
	data = bytes.TrimPrefix(data, []byte{0xEF, 0xBB, 0xBF})
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.UseNumber()
	v, err := decodeValue(dec)
	if err != nil {
		return nil, err
	}
	if _, err := dec.Token(); err != io.EOF {
		return nil, errors.New("unexpected data after the JSON value")
	}
	return v, nil
}

// DecodeObject parses a JSON object.
func DecodeObject(data []byte) (*Object, error) {
	v, err := Decode(data)
	if err != nil {
		return nil, err
	}
	o, ok := v.(*Object)
	if !ok {
		return nil, errors.New("top-level JSON value is not an object")
	}
	return o, nil
}

func decodeValue(dec *json.Decoder) (any, error) {
	tok, err := dec.Token()
	if err != nil {
		return nil, err
	}
	switch t := tok.(type) {
	case json.Delim:
		switch t {
		case '{':
			o := NewObject()
			for dec.More() {
				kt, err := dec.Token()
				if err != nil {
					return nil, err
				}
				key, ok := kt.(string)
				if !ok {
					return nil, errors.New("object key is not a string")
				}
				v, err := decodeValue(dec)
				if err != nil {
					return nil, err
				}
				// Duplicate keys: last one wins, first position kept (Python).
				o.Set(key, v)
			}
			if _, err := dec.Token(); err != nil {
				return nil, err
			}
			return o, nil
		case '[':
			arr := []any{}
			for dec.More() {
				v, err := decodeValue(dec)
				if err != nil {
					return nil, err
				}
				arr = append(arr, v)
			}
			if _, err := dec.Token(); err != nil {
				return nil, err
			}
			return arr, nil
		}
		return nil, fmt.Errorf("unexpected delimiter %v", t)
	default:
		return t, nil
	}
}

// ---------------------------------------------------------------- encoding

// MarshalPython encodes v like json.dumps(v, indent=4, ensure_ascii=False).
func MarshalPython(v any) []byte {
	var b bytes.Buffer
	encode(&b, v, 0, 4)
	return b.Bytes()
}

// MarshalCompact encodes v as compact JSON (for the UI bridge).
func MarshalCompact(v any) []byte {
	var b bytes.Buffer
	encode(&b, v, 0, -1)
	return b.Bytes()
}

// MarshalJSON lets *Object be used with encoding/json (compact, ordered).
func (o *Object) MarshalJSON() ([]byte, error) { return MarshalCompact(o), nil }

func newline(b *bytes.Buffer, level, indent int) {
	if indent < 0 {
		return
	}
	b.WriteByte('\n')
	for i := 0; i < level*indent; i++ {
		b.WriteByte(' ')
	}
}

func encode(b *bytes.Buffer, v any, level, indent int) {
	switch x := v.(type) {
	case nil:
		b.WriteString("null")
	case bool:
		if x {
			b.WriteString("true")
		} else {
			b.WriteString("false")
		}
	case json.Number:
		if x == "" {
			b.WriteString("0")
		} else {
			b.WriteString(string(x))
		}
	case string:
		writeString(b, x)
	case []any:
		if len(x) == 0 {
			b.WriteString("[]")
			return
		}
		b.WriteByte('[')
		for i, e := range x {
			if i > 0 {
				b.WriteByte(',')
			}
			newline(b, level+1, indent)
			encode(b, e, level+1, indent)
		}
		newline(b, level, indent)
		b.WriteByte(']')
	case *Object:
		if x == nil || len(x.keys) == 0 {
			b.WriteString("{}")
			return
		}
		b.WriteByte('{')
		for i, k := range x.keys {
			if i > 0 {
				b.WriteByte(',')
			}
			newline(b, level+1, indent)
			writeString(b, k)
			if indent < 0 {
				b.WriteByte(':')
			} else {
				b.WriteString(": ")
			}
			encode(b, x.m[k], level+1, indent)
		}
		newline(b, level, indent)
		b.WriteByte('}')
	default:
		encode(b, Normalize(v), level, indent)
	}
}

// writeString escapes like Python's json with ensure_ascii=False: only the
// quote, backslash and control characters are escaped.
func writeString(b *bytes.Buffer, s string) {
	b.WriteByte('"')
	for i := 0; i < len(s); {
		c := s[i]
		if c < utf8.RuneSelf {
			switch c {
			case '"':
				b.WriteString(`\"`)
			case '\\':
				b.WriteString(`\\`)
			case '\n':
				b.WriteString(`\n`)
			case '\r':
				b.WriteString(`\r`)
			case '\t':
				b.WriteString(`\t`)
			case '\b':
				b.WriteString(`\b`)
			case '\f':
				b.WriteString(`\f`)
			default:
				if c < 0x20 {
					fmt.Fprintf(b, `\u%04x`, c)
				} else {
					b.WriteByte(c)
				}
			}
			i++
			continue
		}
		r, size := utf8.DecodeRuneInString(s[i:])
		if r == utf8.RuneError && size == 1 {
			b.WriteString(`�`)
			i++
			continue
		}
		// U+2028/2029 are valid in JSON; Python writes them raw too.
		b.WriteString(s[i : i+size])
		i += size
	}
	b.WriteByte('"')
}

// ToPlain converts a tree into plain Go values (map[string]any keeps no
// order) – handy in tests.
func ToPlain(v any) any {
	switch x := v.(type) {
	case *Object:
		m := make(map[string]any, x.Len())
		for _, k := range x.keys {
			m[k] = ToPlain(x.m[k])
		}
		return m
	case []any:
		out := make([]any, len(x))
		for i, e := range x {
			out[i] = ToPlain(e)
		}
		return out
	case json.Number:
		f, _ := x.Float64()
		return f
	}
	return v
}

// Style records how an existing file was laid out on disk so a rewrite keeps
// it (the user's copies went through git and have CRLF line endings and a
// trailing newline; Python itself writes LF without one).
type Style struct {
	CRLF     bool
	Trailing string // "", LF or CRLF after the closing brace
}

// DetectStyle inspects raw file bytes.
func DetectStyle(raw []byte) Style {
	s := Style{CRLF: bytes.Contains(raw, []byte("\r\n"))}
	switch {
	case bytes.HasSuffix(raw, []byte("\r\n")):
		s.Trailing = "\r\n"
	case bytes.HasSuffix(raw, []byte("\n")):
		s.Trailing = "\n"
	}
	return s
}

// Apply converts Python-style output (LF, no trailing newline) to the style.
func (s Style) Apply(out []byte) []byte {
	if s.CRLF {
		out = bytes.ReplaceAll(out, []byte("\n"), []byte("\r\n"))
	}
	return append(out, s.Trailing...)
}
