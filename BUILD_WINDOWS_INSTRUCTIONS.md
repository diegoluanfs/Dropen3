# Building Dropen3 v1.2.0.dev0 on Windows

1. Extract this archive to a normal writable folder (e.g. `C:\Projects\Dropen3_Research`).
2. Inside `Dropen3_Research`, double-click `BUILD_DROPEN3_WINDOWS.cmd`.
3. Python 3.12 and the Python launcher (`py`) must be installed on the **build** computer.
4. The script installs build dependencies in `.venv`, runs pytest and invokes PyInstaller.
5. On success, the portable Windows files are in `Dropen3_Research\dist`:
   - `Dropen3.exe` (graphical application)
   - `Dropen3Doctor.exe` (console diagnostics)
   - `Dropen3Doctor.cmd` (console-safe launcher)

The build window remains open and displays success or error messages. The recipient of the Windows executable does not need Python installed. Verify with actual laboratory video data before research use. Windows executables must be built on Windows, not Linux.

PowerShell alternative, opened at `Dropen3_Research`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build_windows.ps1
.\dist\Dropen3.exe
```
