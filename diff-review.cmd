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
    set GP=
    for /f "delims=" %%i in ('where git.exe 2^>nul') do set GP=%%i
    if defined GP (
        %PYTHON% -b -B -E %~dp0\scripts.d\dr.d\dr.py --git-path %GP% %*
    ) else (
        echo fatal: git not found; unable to generate diffs.
    )
) else (
    echo fatal: python3 not found; unable to generate diffs.
)
