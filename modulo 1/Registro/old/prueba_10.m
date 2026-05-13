% Parámetros del volumen de la imagen
nI = 200;   % Tamaño en la dimensión I
nJ = 200;   % Tamaño en la dimensión J
nK = 127;   % Tamaño en la dimensión K

% Supongamos que ya tienes la imagen cargada como un volumen 3D
% A continuación se usa una imagen de ejemplo (puedes cargar tu propia imagen)
image_volume = randn(nI, nJ, nK);  % Imagen aleatoria para ilustrar

% Definir la matriz de transformación (4x4) previamente discutida
A = [4.07 0 0 -405.23;
     0 4.07 0 -582.41;
     0 0 2.0 -8.5;
     0 0 0 1];

% Generar los índices de voxel (i, j, k)
[i, j, k] = ndgrid(1:nI, 1:nJ, 1:nK);
voxel_coords = [i(:), j(:), k(:)]';  % Aplanar a una matriz 3xN

% Añadir un 1 para la coordenada homogénea
homogeneous_voxel_coords = [voxel_coords; ones(1, numel(i))];

% Transformar las coordenadas de DICOM a RAS
ras_coords = A * homogeneous_voxel_coords;
ras_coords = ras_coords(1:3, :);  % Extraer las coordenadas (X, Y, Z)

% Ahora las coordenadas ras_coords contienen las posiciones en RAS

% Visualizar un corte de la imagen en RAS (ejemplo para un corte específico)
slice_index = 64;  % El índice de corte en el eje Z (puedes cambiarlo)

% Muestra el corte 2D en el plano Z
figure;
imagesc(squeeze(image_volume(:,:,slice_index))); 
axis equal;
title(['Corte en Z = ', num2str(slice_index)]);
xlabel('Posición en I');
ylabel('Posición en J');

% Para visualizar en 3D: Muestra un volumen en 3D usando imágenes con coordenadas RAS
figure;
% Visualización 3D del volumen, asumiendo que las coordenadas están transformadas
% y que la imagen se visualiza con las coordenadas correctas.
% Usamos un "slice" para mostrar un corte en cada dirección.
slice(ras_coords(1,:), ras_coords(2,:), ras_coords(3,:), image_volume, [], [], -640.5); % Corte Z

% Ajustes de visualización para la imagen
colormap('gray');
colorbar;
xlabel('Posición en X (RAS)');
ylabel('Posición en Y (RAS)');
zlabel('Posición en Z (RAS)');
title('Visualización en 3D de la imagen transformada');

