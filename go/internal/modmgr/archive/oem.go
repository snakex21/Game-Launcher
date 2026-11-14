package archive

import (
	"golang.org/x/text/encoding/charmap"
)

// oemPage is the OEM code page used for zip names without the UTF-8 flag
// (set per platform; 852 = Central European, as on Polish Windows).
var oemPage = systemOEMPage()

var oemCharmaps = map[uint32]*charmap.Charmap{
	437: charmap.CodePage437, 850: charmap.CodePage850, 852: charmap.CodePage852, 855: charmap.CodePage855,
	858: charmap.CodePage858, 860: charmap.CodePage860, 862: charmap.CodePage862, 863: charmap.CodePage863,
	865: charmap.CodePage865, 866: charmap.CodePage866,
}

// decodeOEM converts a name from the OEM code page to UTF-8.
func decodeOEM(name string) string {
	cm := oemCharmaps[oemPage]
	if cm == nil {
		cm = charmap.CodePage437
	}
	out, err := cm.NewDecoder().String(name)
	if err != nil {
		return name
	}
	return out
}
