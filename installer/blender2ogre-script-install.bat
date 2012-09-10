@echo off
echo.

IF %2=="" GOTO :ERROR
IF %2=="-" GOTO :ERROR
IF %2=="--\scripts\addons\" GOTO ERROR

echo Copying blender2ogre addon to Blender
echo   from %1
echo   to   %2
copy /Y %1 %2

GOTO :EOF

:ERROR
echo Input parameter for install location is invalid. Please copy %1 manually to Blender\<version>\scripts\addons.
pause
