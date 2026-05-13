% Identificar puntos de referencia en ambas imágenes
clc 
points1 = detectSURFFeatures(CT);
points2 = detectSURFFeatures(PET);

% Extraer coordenadas de puntos de referencia
coords1 = points1.Location;
coords2 = points2.Location;

% Realizar la transformación geométrica
tform = LandmarkRegistration(coords1, coords2);

% Aplicar la transformación a la segunda imagen
img2_aligned = imwarp(PET, tform);
