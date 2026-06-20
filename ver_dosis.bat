@echo off
REM ================================================================
REM ver_dosis.bat — Lanzador del visualizador de resultados DOSIS
REM 
REF: ejecutar_pipeline.bat (mismo patron)
REM 
REF: ver_dosis.py (script Slicer)
REM 
REF: 3Dosim_dosis_scene.mrb (escena con dosis calculada)
REM ================================================================

echo ============================================================
echo  3Dosim — Visualizador de resultados dosimetricos
echo ============================================================
echo.
echo Cargando escena con dosis en 3D Slicer...
echo.
echo Si no se abre automaticamente, revisa:
echo   - Slicer esta instalado en la ruta esperada
echo   - La escena existe en:
echo     C:\MAT\3Dosim\ai-pipe\resultados_dosimetria
echo.

REM Ruta de Slicer
set SLICER_EXE="C:\Users\Sebastian\AppData\Local\slicer.org\Slicer 5.8.1\Slicer.exe"

REM Script de visualizacion
set SCRIPT="C:\programas\3Dosim\3Dosim_v_3.14\3DSlicerModule\SlicerDosim\Testing\PipelineOrchestrator\ver_dosis.py"

REM Ejecutar
echo Lanzando: %SLICER_EXE% --python-script %SCRIPT% %*
echo.

%SLICER_EXE% --python-script %SCRIPT% %*

echo.
echo Slicer cerrado.
pause
