import os
import pydicom
import SimpleITK as sitk
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog

def find_dicom_folders(root_folder):
    """
    Busca subcarpetas que contengan archivos DICOM válidos.
    :param root_folder: Carpeta raíz para buscar DICOM.
    :return: Diccionario con rutas a carpetas DICOM organizadas por modalidad.
    """
    dicom_folders = {}
    for subdir, _, files in os.walk(root_folder):
        for file in files:
            try:
                filepath = os.path.join(subdir, file)
                dicom_file = pydicom.dcmread(filepath, stop_before_pixels=True)
                modality = dicom_file.Modality  # Extraer la modalidad (CT, PET, etc.)
                if modality not in dicom_folders:
                    dicom_folders[modality] = subdir
                break  # Solo necesitamos validar el primer archivo
            except Exception as e:
                continue
    return dicom_folders

def get_dicom_translation(ct_folder, pet_folder):
    """
    Calcula el desplazamiento entre dos volúmenes DICOM (CT y PET).
    :param ct_folder: Carpeta que contiene los archivos DICOM de CT.
    :param pet_folder: Carpeta que contiene los archivos DICOM de PET.
    :return: Traslación (offset) en mm como una tupla (x, y, z).
    """
    # Leer el primer archivo DICOM de cada modalidad
    ct_file = pydicom.dcmread(os.path.join(ct_folder, os.listdir(ct_folder)[0]))
    pet_file = pydicom.dcmread(os.path.join(pet_folder, os.listdir(pet_folder)[0]))

    # Verificar si 'ImagePositionPatient' está presente
    ct_position = ct_file.ImagePositionPatient if 'ImagePositionPatient' in ct_file else [0, 0, 0]
    pet_position = pet_file.ImagePositionPatient if 'ImagePositionPatient' in pet_file else [0, 0, 0]

    # Calcular el desplazamiento en cada eje (x, y, z)
    translation = (
        pet_position[0] - ct_position[0],  # Desplazamiento en X
        pet_position[1] - ct_position[1],  # Desplazamiento en Y
        pet_position[2] - ct_position[2],  # Desplazamiento en Z
    )

    return translation

def load_dicom_volume(folder_path):
    """
    Cargar una carpeta DICOM como volumen 3D usando SimpleITK.
    :param folder_path: Ruta a la carpeta DICOM.
    :return: Imagen 3D cargada en formato SimpleITK.
    """
    reader = sitk.ImageSeriesReader()
    dicom_files = reader.GetGDCMSeriesFileNames(folder_path)
    reader.SetFileNames(dicom_files)
    return reader.Execute()

def show_3d_slices(image, title=""):
    """
    Visualizar cortes axiales, coronales y sagitales de una imagen 3D.
    """
    array = sitk.GetArrayViewFromImage(image)  # Convertir imagen a array numpy

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    slices = [
        array[array.shape[0] // 2, :, :],  # Corte axial
        array[:, array.shape[1] // 2, :],  # Corte coronal
        array[:, :, array.shape[2] // 2],  # Corte sagital
    ]
    titles = ["Axial", "Coronal", "Sagital"]
    
    for ax, slc, t in zip(axes, slices, titles):
        ax.imshow(slc, cmap="gray")
        ax.set_title(f"{title} - {t}")
        ax.axis("off")
    
    plt.show()

def select_folder():
    """
    Abre un cuadro de diálogo para seleccionar una carpeta.
    :return: Ruta de la carpeta seleccionada.
    """
    root = tk.Tk()
    root.withdraw()  # Oculta la ventana principal de tkinter
    folder_selected = filedialog.askdirectory(title="Selecciona la carpeta raíz de DICOM")
    return folder_selected

# Seleccionar carpeta raíz para los archivos DICOM
root_folder = select_folder()

if root_folder:
    print("Carpeta raíz seleccionada:", root_folder)

    # Buscar carpetas DICOM
    dicom_folders = find_dicom_folders(root_folder)
    ct_folder = dicom_folders.get("CT", None)
    pet_folder = dicom_folders.get("PT", None)  # Modalidad PET es "PT" en DICOM

    if ct_folder and pet_folder:
        print("CT Folder:", ct_folder)
        print("PET Folder:", pet_folder)

        # Calcular la traslación entre PET y CT
        translation_offset = get_dicom_translation(ct_folder, pet_folder)
        print("Desplazamiento calculado (mm):", translation_offset)

        # Cargar los volúmenes 3D desde las carpetas DICOM
        image_ct = load_dicom_volume(ct_folder)
        image_pet = load_dicom_volume(pet_folder)

        # Aplicar la traslación a la imagen PET
        translation = sitk.TranslationTransform(3)  # Transformación 3D
        translation.SetOffset(translation_offset)
        image_pet_registered = sitk.Resample(image_pet, image_ct, translation, sitk.sitkNearestNeighbor, 0.0, image_pet.GetPixelID())

        # Visualizar imágenes originales
        show_3d_slices(image_ct, title="CT Original")
        show_3d_slices(image_pet, title="PET Original")

        # Visualizar imágenes registradas
        show_3d_slices(image_ct, title="CT Original")
        show_3d_slices(image_pet_registered, title="PET Registrada")
    else:
        print("No se encontraron carpetas DICOM para CT y PET.")
else:
    print("No se seleccionó ninguna carpeta.")

