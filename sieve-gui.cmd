@echo off
rem Launch the SIEVE window from a fresh checkout: double-click this file, or
rem run it from any shell. Everything Python-side goes through uv, which owns
rem the interpreter and the environment - there is no assumption of a `python`
rem on PATH and no venv to activate first.
rem
rem `--project` rather than `--directory` or a `cd`: the picker the window opens
rem on lists the projects in the current directory (gui/project_select.py), so a
rem launcher that moved the caller into the checkout would answer a question the
rem caller had already answered. Double-clicking still starts here, which is the
rem right list for a fresh checkout.
setlocal
where uv >nul 2>nul || (
    echo SIEVE runs through uv, which is not on PATH.
    echo Install it from https://docs.astral.sh/uv/ and run this again.
    pause
    exit /b 1
)
rem `"%~dp0."` - %~dp0 ends in a backslash, which would escape the closing quote.
uv run --project "%~dp0." sieve-gui %*
rem A double-click has no console to read the traceback from once this returns,
rem so a failure holds the window open. A clean exit closes it.
if errorlevel 1 pause
