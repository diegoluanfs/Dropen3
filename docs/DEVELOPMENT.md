# Dropen3 — Development Environment

This document describes how to configure, run, test, and contribute to Dropen3 on Windows and Linux.

## 1. Requirements

Before starting, install:

- Python 3.12
- Git
- Visual Studio Code (recommended)
- Python extension for Visual Studio Code
- A graphical desktop environment to run the application GUI

Check the installations:

```bash
python --version
git --version
code --version
```

On Windows, use `py -3.12 --version` if `python` is not recognized. On Linux, use `python3.12 --version`.

## 2. Clone the repository

Clone the project's GitHub repository:

```bash
git clone <REPOSITORY_URL>
cd dropen3
```

Replace `<REPOSITORY_URL>` with the actual repository URL.

## 3. Windows development setup

Open PowerShell in the project directory.

### Create the virtual environment

```powershell
py -3.12 -m venv .venv
```

### Activate the environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If execution policies prevent activation, you can use the virtual environment's Python executable directly without activating it.

### Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

The editable installation (`-e`) makes local source-code changes available without reinstalling the package.

### Start Dropen3

```powershell
python -m dropen3 gui
```

### Run tests

```powershell
python -m pytest -q
```

### Run system diagnostics

```powershell
python -m dropen3 doctor --no-pause
```

### Deactivate the environment

```powershell
deactivate
```

## 4. Linux development setup

The following system package commands target Ubuntu/Debian-based distributions.

### Install operating system dependencies

```bash
sudo apt update
sudo apt install -y \
    git \
    python3-tk \
    libgl1 \
    libglib2.0-0
```

Python 3.12, its venv module, and pip must also be installed. Their package names and availability depend on the Linux distribution and version.

Check Python:

```bash
python3.12 --version
```

### Create the virtual environment

```bash
python3.12 -m venv .venv
```

If creation fails because `ensurepip` or the venv module is missing, install the appropriate Python 3.12 venv package for your distribution.

### Activate the environment

```bash
source .venv/bin/activate
```

### Install project dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

### Start Dropen3

```bash
python -m dropen3 gui
```

A graphical desktop session is required for the application interface.

### Run tests

```bash
python -m pytest -q
```

### Run system diagnostics

```bash
python -m dropen3 doctor --no-pause
```

### Deactivate the environment

```bash
deactivate
```

For additional Linux-specific instructions, see `docs/LINUX.md`.

## 5. Using Visual Studio Code

Open the project:

```bash
code .
```

Install the Microsoft Python extension.

Select the Python interpreter:

1. Open the Command Palette with `Ctrl+Shift+P`.
2. Select `Python: Select Interpreter`.
3. Choose the interpreter inside `.venv`.

Interpreter paths:

Windows:

```text
.venv\Scripts\python.exe
```

Linux:

```text
.venv/bin/python
```

After selecting the interpreter, use the integrated terminal to run the application or tests.

## 6. Daily development workflow

Before starting work:

```bash
git switch main
git pull origin main
git switch -c feature/my-feature
```

If the virtual environment already exists, activate it.

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux:

```bash
source .venv/bin/activate
```

Start the application:

```bash
python -m dropen3 gui
```

Run the test suite before submitting changes:

```bash
python -m pytest -q
```

Commit your changes:

```bash
git add .
git commit -m "feat: describe implemented feature"
git push -u origin feature/my-feature
```

Open a Pull Request for code review.

## 7. Scientific development rules

Dropen3 is research-oriented scientific software.

Changes to scientific algorithms must:

- Preserve reproducibility and measurement traceability.
- Include automated tests when applicable.
- Document changes to equations, measurement definitions, and numerical processing.
- Avoid modifying scientific behavior without review.
- Be tested using representative experimental data before scientific acceptance.

Passing automated tests alone does not establish experimental or metrological validity.

For contribution rules, consult `CONTRIBUTING.md`. For validation requirements, consult `docs/VALIDATION.md`.

## 8. Troubleshooting

**Python interpreter not found:** verify that Python 3.12 is installed and accessible.

**Virtual environment activation fails on Windows:** invoke `.venv\Scripts\python.exe` directly.

**Tkinter unavailable on Linux:** install the Tk package compatible with the Python interpreter.

**OpenCV fails to load system libraries:** check that the required graphical libraries are installed.

**GUI cannot start on Linux:** ensure that the session has access to a graphical display.

**Tests fail after pulling changes:** activate the environment and reinstall dependencies using `python -m pip install -e ".[test]"`.

## 9. Platform support

| Capability | Windows | Linux |
|---|---|---|
| Python development | Supported | Supported |
| Editable installation | Supported | Supported |
| Automated tests | Supported | Supported |
| System Doctor | Supported | Supported |
| Tkinter graphical interface | Requires desktop | Requires desktop |
| Windows `.exe` build | Windows only | Not supported |

Linux runtime compatibility must be verified on the targeted distribution. A successful Windows test run does not automatically establish Linux compatibility.