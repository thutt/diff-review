@echo off
rem  Copyright (c) 2025  Logic Magicians Software.
rem  All Rights Reserved.
rem  Licensed under Gnu GPL V3.
rem w
rem  This wrapper script facilitates invoking the self-review Python
rem  script.
rem

python3 -B %~dp0\scripts.d\vr.d\vr.py %*
