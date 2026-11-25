@echo off
REM Update the search index from the files in data\library, without opening the app:
REM new files are embedded, documents whose file was deleted are removed.
REM To embed everything again:  build_index.bat --rebuild
cd /d "%~dp0"
uv run python -m scanya_ae_afa_updated0209_2_5.build_index %*
pause
