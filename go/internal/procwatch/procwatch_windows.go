//go:build windows

package procwatch

import (
	"strings"
	"unsafe"

	"golang.org/x/sys/windows"
)

// List returns a snapshot of running processes.
func List() ([]Process, error) {
	snap, err := windows.CreateToolhelp32Snapshot(windows.TH32CS_SNAPPROCESS, 0)
	if err != nil {
		return nil, err
	}
	defer windows.CloseHandle(snap)
	var e windows.ProcessEntry32
	e.Size = uint32(unsafe.Sizeof(e))
	if err := windows.Process32First(snap, &e); err != nil {
		return nil, err
	}
	var out []Process
	for {
		pid := e.ProcessID
		p := Process{PID: pid, PPID: e.ParentProcessID, Name: strings.ToLower(windows.UTF16ToString(e.ExeFile[:]))}
		if pid != 0 {
			p.Exe = exePath(pid)
			p.cmdline = func() string { return cmdLine(pid) }
		}
		out = append(out, p)
		if err := windows.Process32Next(snap, &e); err != nil {
			break
		}
	}
	return out, nil
}

func exePath(pid uint32) string {
	h, err := windows.OpenProcess(windows.PROCESS_QUERY_LIMITED_INFORMATION, false, pid)
	if err != nil {
		return ""
	}
	defer windows.CloseHandle(h)
	buf := make([]uint16, windows.MAX_LONG_PATH)
	n := uint32(len(buf))
	if err := windows.QueryFullProcessImageName(h, 0, &buf[0], &n); err != nil {
		return ""
	}
	return windows.UTF16ToString(buf[:n])
}

// cmdLine reads another process's command line (Windows 8.1+).
func cmdLine(pid uint32) string {
	h, err := windows.OpenProcess(windows.PROCESS_QUERY_LIMITED_INFORMATION, false, pid)
	if err != nil {
		return ""
	}
	defer windows.CloseHandle(h)
	var need uint32
	_ = windows.NtQueryInformationProcess(h, windows.ProcessCommandLineInformation, nil, 0, &need)
	if need == 0 || need > 1<<20 {
		return ""
	}
	buf := make([]byte, need)
	if err := windows.NtQueryInformationProcess(h, windows.ProcessCommandLineInformation, unsafe.Pointer(&buf[0]), need, &need); err != nil {
		return ""
	}
	us := (*windows.NTUnicodeString)(unsafe.Pointer(&buf[0]))
	if us.Buffer == nil || us.Length == 0 {
		return ""
	}
	return windows.UTF16PtrToString(us.Buffer)
}

// Terminate ends one process.
func Terminate(pid uint32) error {
	h, err := windows.OpenProcess(windows.PROCESS_TERMINATE, false, pid)
	if err != nil {
		return err
	}
	defer windows.CloseHandle(h)
	return windows.TerminateProcess(h, 1)
}
