@echo off
title Terminal Pendu Server

echo ===============================================
echo            TERMINAL PENDU SERVER
echo ===============================================
echo.
echo Demarrage du serveur web...
echo.

REM Verifier si Python est installe
python --version >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Python n'est pas installe ou pas dans le PATH
    echo.
    echo Veuillez installer Python depuis https://python.org
    echo Ou depuis le Microsoft Store
    pause
    exit /b 1
)

REM Installer les dependances si necessaire
echo Installation des dependances...
python -m pip install -r requirements.txt

REM Lancer l'API
echo.
echo Demarrage de l'API FastAPI...
echo.
echo Interface web disponible sur:
echo.
echo Appuyez sur Ctrl+C pour arreter le serveur
echo.
python api.py