@echo off
REM Batch script to run tests with virtual environment activated
REM Usage: run_tests.bat

call venv\Scripts\activate.bat

echo Running simple tests...
python test_simple.py

echo.
echo Running pytest suite...
pytest test_mcp_server.py -v

pause

