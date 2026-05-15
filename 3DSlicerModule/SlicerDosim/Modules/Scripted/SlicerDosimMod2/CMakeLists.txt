#-----------------------------------------------------------------------------
set(MODULE_NAME SlicerDosimMod2)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  __init__.py
  SlicerDosimMod2.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/UI/SlicerDosimMod2.ui
  Resources/UI/Icons/SlicerDosimMod2.svg
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  )
