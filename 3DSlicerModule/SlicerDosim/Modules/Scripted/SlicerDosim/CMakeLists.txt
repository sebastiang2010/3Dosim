#-----------------------------------------------------------------------------
set(MODULE_NAME SlicerDosim)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  __init__.py
  SlicerDosim.py
  SlicerDosimLib/__init__.py
  SlicerDosimLib/config.py
  SlicerDosimLib/phantom_segmentation.py
  SlicerDosimLib/segmentation.py
  SlicerDosimLib/registration.py
  SlicerDosimLib/mcnp_generator.py
  SlicerDosimLib/mcnp_materials.py
  SlicerDosimLib/mcnp_geometry.py
  SlicerDosimLib/mcnp_source.py
  SlicerDosimLib/mcnp_tallies.py
  SlicerDosimLib/dosimetry.py
  SlicerDosimLib/mctal_parser.py
  SlicerDosimLib/dvh_analysis.py
  SlicerDosimLib/utils.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/UI/SlicerDosim.ui
  Resources/UI/Icons/SlicerDosim.svg
  Resources/Config/tissue_config.json
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  )
