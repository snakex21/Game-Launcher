package procwatch

import (
	"os"
	"reflect"
	"runtime"
	"strings"
	"testing"
)

func procs() []Process {
	return []Process{
		{PID: 10, Name: "dsj4.exe", Exe: `D:\Gry\DSJ4\DSJ4.exe`},
		{PID: 11, Name: "dsj4.exe", Exe: `C:\Inne\DSJ4.exe`}, // same name, other game
		{PID: 12, PPID: 10, Name: "helper.exe", Exe: `D:\Gry\DSJ4\helper.exe`},
		{PID: 20, Name: "pcsx2-qt.exe", Exe: `H:\Emu\pcsx2-qt.exe`, cmdline: func() string { return `"H:\Emu\pcsx2-qt.exe" -fullscreen "H:\ROM\okami.iso"` }},
		{PID: 21, Name: "pcsx2-qt.exe", Exe: `H:\Emu\pcsx2-qt.exe`, cmdline: func() string { return `"H:\Emu\pcsx2-qt.exe" "H:\ROM\re4.iso"` }},
		{PID: 30, Name: "protected.exe"}, // exe path unreadable
	}
}

func TestMatchPC(t *testing.T) {
	got := Match(Target{Game: "DSJ4", Exes: []string{`d:/gry/dsj4/dsj4.exe`}}, procs(), nil)
	if !reflect.DeepEqual(got, []uint32{10}) {
		t.Fatal(got)
	}
	got = Match(Target{Game: "P", Exes: []string{`X:\p\protected.exe`}}, procs(), nil)
	if !reflect.DeepEqual(got, []uint32{30}) {
		t.Fatal("name fallback when the path is unreadable:", got)
	}
}

func TestMatchEmulatorByROM(t *testing.T) {
	got := Match(Target{Game: "Okami", Emulator: true, Exes: []string{`H:\Emu\pcsx2-qt.exe`}, ROM: `H:\ROM\okami.iso`}, procs(), nil)
	if !reflect.DeepEqual(got, []uint32{20}) {
		t.Fatal(got)
	}
}

func TestDescendants(t *testing.T) {
	got := Descendants([]uint32{10}, procs())
	if !reflect.DeepEqual(got, []uint32{12, 10}) {
		t.Fatal(got)
	}
}

func TestListFindsSelf(t *testing.T) {
	if runtime.GOOS != "windows" {
		t.Skip()
	}
	ps, err := List()
	if err != nil {
		t.Fatal(err)
	}
	self := uint32(os.Getpid())
	for _, p := range ps {
		if p.PID == self {
			exe, _ := os.Executable()
			if !strings.EqualFold(p.Exe, exe) {
				t.Errorf("exe %q vs %q", p.Exe, exe)
			}
			if !strings.Contains(strings.ToLower(p.CmdLine()), ".test") {
				t.Errorf("cmdline %q", p.CmdLine())
			}
			return
		}
	}
	t.Fatal("own process not listed")
}
