#-----------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.16)

#-----------------------------------------------------------------------------
if(NOT DEFINED Slicer_SOURCE_DIR)
  # Extension build
  project(SlicerDosim)

  find_package(Slicer REQUIRED)
  include("${Slicer_USE_FILE}")

  add_subdirectory(Modules)
endif()

#-----------------------------------------------------------------------------
# Extension dependencies
set(EXTENSION_DEPENDS "SlicerRT" "SegmentEditorExtraEffects")

#-----------------------------------------------------------------------------
# Extension description
set(EXTENSION_NAME "SlicerDosim")
set(EXTENSION_HOMEPAGE "https://github.com/example/SlicerDosim")
set(EXTENSION_CATEGORY "Radiotherapy")
set(EXTENSION_CONTRIBUTORS "Tu Nombre <email>")
set(EXTENSION_DESCRIPTION "Modulo de dosimetria 3D para radioembolizacion hepatica (Y-90). Integra segmentacion, registro, generacion MCNP y analisis DVH/TCP/NTCP.")
set(EXTENSION_ICONURL "https://github.com/example/SlicerDosim/icon.png")
set(EXTENSION_SCREENSHOTURLS "")
set(EXTENSION_STATUS "Beta")

#-----------------------------------------------------------------------------
if(NOT DEFINED Slicer_SOURCE_DIR)
  # Extension build
  if(NOT "${CMAKE_SOURCE_DIR}" STREQUAL "${CMAKE_CURRENT_SOURCE_DIR}")
    return()
  endif()
  slicer_create_extension_build(FILES "")
endif()
