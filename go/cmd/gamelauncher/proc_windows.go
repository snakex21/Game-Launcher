//go:build windows

package main

import (
	"time"

	"golang.org/x/sys/windows"
)

// processStart is the OS creation time of this process (so start-up timing
// includes the loader, not just main()).
func processStart() time.Time {
	var c, e, k, u windows.Filetime
	if err := windows.GetProcessTimes(windows.CurrentProcess(), &c, &e, &k, &u); err != nil {
		return time.Now()
	}
	return time.Unix(0, c.Nanoseconds())
}
