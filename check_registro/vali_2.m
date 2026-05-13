%% Configuración Inicial
clear; clc; close all;

% Parámetros generales
s_original = [100, 100, 50];       % Tamaño original [filas, columnas, slices]
voxel_original = [2, 2, 1];        % Resolución original (mm)
new_voxel = [4, 4, 2];             % Nueva resolución PET (mm)
centro_esfera = [30, 15, 25];      % Centro de la esfera PET (Y,X,Z)
radio_esfera = 10;                 % Radio de la esfera (vóxeles)

%% 1. Generar PET sintético con degradado
[X, Y, Z] = meshgrid(1:s_original(2), 1:s_original(1), 1:s_original(3));
distance = sqrt((X - centro_esfera(2)).^2 + (Y - centro_esfera(1)).^2 + (Z - centro_esfera(3)).^2);

% Degradado gaussiano (actividad máxima = 5 Bq/vóxel)
PET_original = 5 * exp(-(distance.^2)/(2*(radio_esfera/2)^2));
PET_original(distance > radio_esfera) = 0;

% Visualizar slice central PET original
figure;
imshow(PET_original(:,:,centro_esfera(3)), [0 5]);
title('PET Original (Slice 25)');
colormap(jet); colorbar;

%% 2. Generar CT sintético (cubo simulado)
CT = zeros(s_original);
CT(20:40, 10:30, 20:30) = 60;    % Cubo representando hígado (60 HU)
CT(70:90, 60:80, 10:40) = 1000;   % Cubo representando hueso (1000 HU)

% Visualizar slice central CT
figure;
imshow(CT(:,:,centro_esfera(3)), [-1000 1000]);
title('CT Sintético (Slice 25)');
colormap(gray); colorbar;

%% 3. Desplazar PET (simular mala alineación)
desplazamiento = [0, 20, 0]; % Desplazamiento en [Y, X, Z]
PET_desplazado = circshift(PET_original, desplazamiento);

% Visualizar superposición desplazada
figure;
imshow(CT(:,:,centro_esfera(3)), [-1000 1000]);
hold on;
h = imshow(PET_desplazado(:,:,centro_esfera(3)), [0 5]);
set(h, 'AlphaData', 0.3);
title('PET Desplazado vs CT');
colormap(jet); colorbar;

%% 4. Reducir resolución del PET
scale_factors = voxel_original ./ new_voxel;
new_size = floor(s_original .* scale_factors);

% Reducción con conservación de actividad
PET_reducido = imresize3(PET_desplazado, new_size, 'Method', 'box');
PET_reducido = PET_reducido * prod(new_voxel./voxel_original);

% Visualizar PET reducido
figure;
imshow(PET_reducido(:,:,round(centro_esfera(3)*scale_factors(3))), [0 5]);
title('PET Reducido (4×4×2 mm)');
colormap(jet); colorbar;

%% 5. Registro PET-CT (simulación manual)
PET_corregido = circshift(PET_reducido, -desplazamiento./scale_factors); % Corregir desplazamiento

% Reducir CT para coincidir con PET reducido
CT_reducido = imresize3(CT, new_size, 'Method', 'nearest');

%% 6. Validación Visual
% Superposición PET corregido + CT
slice = round(centro_esfera(3)*scale_factors(3));
figure;
imshow(CT_reducido(:,:,slice), [-1000 1000]);
hold on;
h = imshow(PET_corregido(:,:,slice), [0 5]);
set(h, 'AlphaData', 0.3);
title('PET Corregido vs CT');
colormap(jet); colorbar;

%% 7. Validación Cuantitativa
% Conservación de actividad
actividad_original = sum(PET_original(:));
actividad_final = sum(PET_corregido(:));
error_actividad = abs(actividad_original - actividad_final)/actividad_original*100;

fprintf('Conservación de actividad:\n');
fprintf('Original: %.2f Bq\nFinal: %.2f Bq\nError: %.2f%%\n\n',...
        actividad_original, actividad_final, error_actividad);

% Posición del centroide
[y_orig, x_orig, z_orig] = ind2sub(size(PET_original), find(PET_original > 0));
centroide_original = mean([x_orig, y_orig, z_orig]);

[y_corr, x_corr, z_corr] = ind2sub(size(PET_corregido), find(PET_corregido > 0));
centroide_corregido = mean([x_corr, y_corr, z_corr])./scale_factors;

error_posicion = norm(centroide_original - centroide_corregido);
fprintf('Precisión de registro:\n');
fprintf('Error posición: %.2f vóxeles originales\n', error_posicion);

%% 8. Visualización 3D (requiere Image Processing Toolbox)
% Para PET original
figure;
volshow(PET_original, 'Colormap', jet, 'Renderer', 'MaximumIntensity');
title('Actividad PET Original 3D');

% Para PET corregido
figure;
volshow(PET_corregido, 'Colormap', jet, 'Renderer', 'MaximumIntensity');
title('Actividad PET Corregido 3D');