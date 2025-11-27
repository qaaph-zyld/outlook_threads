@echo off
echo ========================================
echo Transport Thread Manager - Test Suite
echo ========================================
echo.

REM Activate virtual environment if exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Run pytest with coverage
echo Running tests with coverage...
echo.
python -m pytest tests/ -v --tb=short

echo.
echo ========================================
echo Test run complete!
echo ========================================
pause
