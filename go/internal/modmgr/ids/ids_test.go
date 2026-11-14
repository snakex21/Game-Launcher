package ids

import "testing"

func TestSortableAndValid(t *testing.T) {
	prev := ""
	seen := map[string]bool{}
	for i := 0; i < 5000; i++ {
		id := New()
		if !Valid(id) || seen[id] || id <= prev {
			t.Fatalf("bad id %q after %q", id, prev)
		}
		seen[id] = true
		prev = id
	}
	for _, bad := range []string{"", "../../x", "01ARZ3NDEKTSV4RRFFQ69G5FA", "01ARZ3NDEKTSV4RRFFQ69G5FAU", "01arz3ndektsv4rrffq69g5fav"} {
		if Valid(bad) {
			t.Errorf("%q valid", bad)
		}
	}
}
