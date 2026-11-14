//go:build windows

package launch

import (
	"os/exec"
	"syscall"
)

// detach: own process group, so the game ignores the launcher's console
// signals and keeps running after the launcher exits.
func detach(cmd *exec.Cmd) {
	const createNewProcessGroup = 0x00000200
	cmd.SysProcAttr = &syscall.SysProcAttr{CreationFlags: createNewProcessGroup}
}
