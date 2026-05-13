import os
import pydicom
import SimpleITK as sitk
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog

def check_dicom_folder(folder_path):
    """
    Verifica si la carpeta contiene archivos DICOM válidos.
    :param folder_path: Ruta de la carpeta a verificar.
    :return: True si contiene archivos DICOM válidos, False de lo contrario.
    """
    for file in os.listdir(folder_path):
        try:
            filepath = os.path.join(folder_path, file)
            pydicom.dcmread(filepath, stop_before_pixels=True)
            return True
        except:
            continue
    return False

def get_dicom_translation(ct_folder, pet_folder):
    """
    Calcula el desplazamiento entre dos volúmenes DICOM (CT y PET).
    :param ct_folder: Carpeta que contiene los archivos DICOM de CT.
    :param pet_folder: Carpeta que contiene los archivos DICOM de PET.
    :return: Traslación (offset) en mm como una tupla (x, y, z).
    """
    ct_file = pydicom.dcmread(os.path.join(ct_folder, os.listdir(ct_folder)[0]))
    pet_file = pydicom.dcmread(os.path.join(pet_folder, os.listdir(pet_folder)[0]))

    ct_position = ct_file.ImagePositionPatient if 'ImagePositionPatient' in ct_file else [0, 0, 0]
    pet_position = pet_file.ImagePositionPatient if 'ImagePositionPatient' in pet_file else [0, 0, 0]

    translation = (
        pet_position[0] - ct_position[0],
        pet_position[1] - ct_position[1],
        pet_position[2] - ct_position[2],
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

def show_3d_slices_overlay(ct_image, pet_image, title=""):
    """
    Visualizar cortes axiales, coronales y sagitales de una imagen 3D y superponer otra imagen.
    :param ct_image: Imagen 3D de CT.
    :param pet_image: Imagen 3D de PET.
    :param title: Título de la figura.
    """
    # Convertir las imágenes de SimpleITK a arrays de numpy
    ct_array = sitk.GetArrayViewFromImage(ct_image)
    pet_array = sitk.GetArrayViewFromImage(pet_image)

    # Obtener información sobre el espacio (resolución y posición)
    ct_origin = ct_image.GetOrigin()
    ct_spacing = ct_image.GetSpacing()
    pet_origin = pet_image.GetOrigin()
    pet_spacing = pet_image.GetSpacing()

    slices_ct = [
        ct_array[ct_array.shape[0] // 2, :, :],  # Corte axial
        ct_array[:, ct_array.shape[1] // 2, :],  # Corte coronal
        ct_array[:, :, ct_array.shape[2] // 2],  # Corte sagital
    ]
    
    slices_pet = [
        pet_array[pet_array.shape[0] // 2, :, :],  # Corte axial
        pet_array[:, pet_array.shape[1] // 2, :],  # Corte coronal
        pet_array[:, :, pet_array.shape[2] // 2],  # Corte sagital
    ]
    
    titles = ["Axial", "Coronal", "Sagital"]
    
    # Usar plt.show() en el último momento para mantener la ventana abierta
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, ct_slc, pet_slc, t in zip(axes, slices_ct, slices_pet, titles):
        # Mostrar CT en escala de grises
        ax.imshow(ct_slc, cmap="gray", alpha=1.0)  # Mostrar CT con opacidad completa
        # Superponer PET con transparencia de 50%
        ax.imshow(pet_slc, cmap="jet", alpha=0.5)  # Superponer PET con transparencia
        ax.set_title(f"{title} - {t}")
        ax.axis("off")
    plt.tight_layout()
    plt.show()

def select_folder(title):
    """
    Abre un cuadro de diálogo para seleccionar una carpeta.
    :param title: Título del cuadro de diálogo.
    :return: Ruta de la carpeta seleccionada.
    """
    root = tk.Tk()
    root.withdraw()
    return filedialog.askdirectory(title=title)

# Seleccionar carpetas para CT y PET
ct_folder = select_folder("Selecciona la carpeta que contiene los archivos DICOM de CT")
pet_folder = select_folder("Selecciona la carpeta que contiene los archivos DICOM de PET")

if ct_folder and pet_folder:
    if not check_dicom_folder(ct_folder):
        print("La carpeta seleccionada para CT no contiene archivos DICOM válidos.")
    elif not check_dicom_folder(pet_folder):
        print("La carpeta seleccionada para PET no contiene archivos DICOM válidos.")
    else:
        print("CT Folder:", ct_folder)
        print("PET Folder:", pet_folder)

        # Calcular el desplazamiento entre CT y PET
        translation_offset = get_dicom_translation(ct_folder, pet_folder)
        print("Desplazamiento calculado (mm):", translation_offset)

        # Cargar las imágenes DICOM como volúmenes 3D
        image_ct = load_dicom_volume(ct_folder)
        image_pet = load_dicom_volume(pet_folder)

        # Aplicar la traslación solo a la imagen PET (no mover la CT)
        new_origin = [image_pet.GetOrigin()[i] - translation_offset[i] for i in range(3)]  # Usar image_pet
        image_pet.SetOrigin(new_origin)

        print("Visualizando CT Original con PET superpuesto...")
        show_3d_slices_overlay(image_ct, image_pet, title="CT con PET superpuesto")
        p=1
else:
    print("No se seleccionaron ambas carpetas.")
