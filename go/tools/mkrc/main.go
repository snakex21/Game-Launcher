// Command mkrc writes the Windows resource (icon + VERSIONINFO, so the exe's
// Properties show the version) and compiles it with windres (MinGW-w64)
// into cmd/gamelauncher/rsrc_windows_amd64.syso, which go build links in.
//
//	go run ./tools/mkrc 0.2.0
package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"
)

func main() {
	ver := "0.0.0"
	if len(os.Args) > 1 {
		ver = os.Args[1]
	}
	m := regexp.MustCompile(`^v?(\d+)\.(\d+)\.(\d+)`).FindStringSubmatch(ver)
	nums := []int{0, 0, 0, 0}
	if m != nil {
		for i := 0; i < 3; i++ {
			nums[i], _ = strconv.Atoi(m[i+1])
		}
	}
	comma := fmt.Sprintf("%d,%d,%d,%d", nums[0], nums[1], nums[2], nums[3])
	dir := filepath.Join("cmd", "gamelauncher")
	rc := fmt.Sprintf(`#include <winver.h>
1 ICON "icon.ico"
1 VERSIONINFO
FILEVERSION %[1]s
PRODUCTVERSION %[1]s
FILEFLAGSMASK 0x3fL
FILEFLAGS 0x0L
FILEOS VOS_NT_WINDOWS32
FILETYPE VFT_APP
FILESUBTYPE 0x0L
BEGIN
  BLOCK "StringFileInfo"
  BEGIN
    BLOCK "041504B0"
    BEGIN
      VALUE "CompanyName", "snakex21"
      VALUE "FileDescription", "Game Launcher"
      VALUE "FileVersion", "%[2]s"
      VALUE "InternalName", "GameLauncher"
      VALUE "LegalCopyright", "(c) %[3]d snakex21, MIT"
      VALUE "OriginalFilename", "GameLauncher.exe"
      VALUE "ProductName", "Game Launcher"
      VALUE "ProductVersion", "%[2]s"
    END
  END
  BLOCK "VarFileInfo"
  BEGIN
    VALUE "Translation", 0x415, 1200
  END
END
`, comma, strings.ReplaceAll(ver, `"`, ""), time.Now().Year())
	rcPath := filepath.Join(dir, "rsrc.rc")
	if err := os.WriteFile(rcPath, []byte(rc), 0o644); err != nil {
		log.Fatal(err)
	}
	defer os.Remove(rcPath)
	cmd := exec.Command("windres", "-O", "coff", "--codepage=65001", "-i", "rsrc.rc", "-o", "rsrc_windows_amd64.syso")
	cmd.Dir = dir
	cmd.Stdout, cmd.Stderr = os.Stdout, os.Stderr
	if err := cmd.Run(); err != nil {
		log.Fatalf("windres: %v", err)
	}
	fmt.Println("OK ->", filepath.Join(dir, "rsrc_windows_amd64.syso"), ver)
}
