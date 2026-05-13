% Parámetros del volumen de la imagen
nI = 200;   % Tamaño en la dimensión I
nJ = 200;   % Tamaño en la dimensión J
nK = 127;   % Tamaño en la dimensión K


pos3DSlicer=A*[0 0 0 1];


% Supongamos que ya tienes la imagen cargada como un volumen 3D
% A continuación se usa una imagen aleatoria para ilustrar
image_volume = randn(nI, nJ, nK);  % Imagen aleatoria para ilustrar

% Definir la matriz de transformación (4x4) previamente discutida
A = [4.07 0 0 -405.23;
     0 4.07 0 -582.41;
     0 0 2.0 -8.5;
     0 0 0 1];

%pos3DSlicer=A*[0 0 0 1]';


% Definir el índice del corte axial
slice_index = 64;

% Obtener las coordenadas del corte axial en el volumen (en coordenadas de voxel)
% Tomamos el corte en el índice Z = slice_index (en la dimensión K)
slice_voxel_coords = [ones(nI, nJ)*slice_index];  % Solo en el eje Z, el índice es fijo

% Generar los índices de voxel (i, j, k)
[i, j] = ndgrid(1:nI, 1:nJ);  % Las coordenadas de voxel para la dimensión I y J
slice_voxel_coords = [i(:)'; j(:)'; slice_index*ones(1, numel(i))];

% Añadir un 1 para la coordenada homogénea
homogeneous_voxel_coords = [slice_voxel_coords; ones(1, size(slice_voxel_coords, 2))];

% Transformar las coordenadas de DICOM a RAS
ras_coords = A * homogeneous_voxel_coords;
ras_coords = ras_coords(1:3, :);  % Extraer las coordenadas (X, Y, Z)

% Visualizar el corte axial en coordenadas RAS (Figura 1)
figure;
imagesc(ras_coords(1,:), ras_coords(2,:), squeeze(image_volume(:,:,slice_index))); 
axis equal;
title(['Corte axial en Z = ', num2str(slice_index), ' en coordenadas RAS']);
xlabel('Posición en X (RAS)');
ylabel('Posición en Y (RAS)');
colorbar;
colormap('gray');

% Visualizar el corte axial en coordenadas ijk (DICOM) (Figura 2)
figure;
imagesc(i(1,:), j(:,1), squeeze(image_volume(:,:,slice_index))); 
axis equal;
title(['Corte axial en Z = ', num2str(slice_index), ' en coordenadas ijk (DICOM)']);
xlabel('Posición en I (DICOM)');
ylabel('Posición en J (DICOM)');
colorbar;
colormap('gray');
