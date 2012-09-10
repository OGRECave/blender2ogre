@echo off
echo.

IF %1=="" GOTO :ERROR
IF %1=="-" GOTO :ERROR
IF %1=="--\scripts\addons\io_export_ogreDotScene.py" GOTO ERROR

echo Removing addon from %1
del /Q %1

GOTO :EOF

:ERROR
echo Input parameter for install location is invalid. Please remove io_export_ogreDotScene.py manually from Blender\<version>\scripts\addons.
pause
