@echo off
echo ===================================================
echo  3Dosim Pipeline v3.14 - Lanzador
echo ===================================================
echo.

:: Cerrar cualquier Slicer abierto
echo [1/3] Cerrando instancias previas de 3D Slicer...
taskkill /F /IM Slicer.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo  OK
echo.

:: Configurar rutas
set SLICER_EXE="C:\Users\Sebastian\AppData\Local\slicer.org\Slicer 5.8.1\Slicer.exe"
set PIPELINE_SCRIPT="C:\programas\3Dosim\3Dosim_v_3.14\3DSlicerModule\SlicerDosim\Testing\PipelineOrchestrator\main.py"
set DATA_DIR="C:\MAT\3Dosim\pacientes-\pacientes\Paciente_2"

:: Elegir segmentador: solo totalsegmentator
set SEGMENTER=totalsegmentator

echo [2/3] Iniciando pipeline con segmentador: %SEGMENTER%
echo.
echo  Datos: %DATA_DIR%
echo  Script: %PIPELINE_SCRIPT%
echo.

:: Ejecutar pipeline
%SLICER_EXE% --python-script %PIPELINE_SCRIPT% --data-dir %DATA_DIR% --segmenter %SEGMENTER% --reset

echo.
echo [3/3] Pipeline finalizado
echo.
pause
