# Asegúrate de que la imagen PET se haya cargado correctamente
image_ct = load_dicom_volume(ct_folder)
image_pet = load_dicom_volume(pet_folder)

# Verifica las dimensiones y orígenes de ambas imágenes
print(f"CT image size: {image_ct.GetSize()}")
print(f"PET image size: {image_pet.GetSize()}")
print(f"CT image origin: {image_ct.GetOrigin()}")
print(f"PET image origin: {image_pet.GetOrigin()}")

# Traslación calculada entre CT y PET
translation_offset = get_dicom_translation(ct_folder, pet_folder)
print(f"Desplazamiento calculado (mm): {translation_offset}")

# Ajustar el origen de la imagen PET según la traslación calculada
# Aquí estamos utilizando 'image_pet' y no 'pet_image'
new_origin = [image_pet.GetOrigin()[i] - translation_offset[i] for i in range(3)]
image_pet.SetOrigin(new_origin)

# Ahora la imagen PET debería estar correctamente registrada en el espacio de la imagen CT



