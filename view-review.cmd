@echo off
rem  Copyright (c) 2025  Logic Magicians Software.
rem  All Rights Reserved.
rem  Licensed under Gnu GPL V3.
rem
rem  This wrapper script facilitates invoking the self-review Python
rem  script.
rem

set PYTHON=
for /f "delims=" %%i in ('where python3.exe 2^>nul') do set PYTHON=%%i
if defined PYTHON (
    %PYTHON%  -b -B -E  %~dp0\scripts.d\vr.d\vr.py %*
) else (
    echo fatal: python3 not found; unable to generate diffs.
)
