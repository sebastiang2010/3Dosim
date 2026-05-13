clc;
close all;

% Cargar una imagen DICOM y sus metadatos
%dicom_path = 'ruta_a_tu_archivo.dcm'; % Cambia esto por tu archivo DICOM
%image = dicomread(dicom_path);         % Leer la imagen
%info = dicominfo(dicom_path);          % Obtener los metadatos

% Extraer los valores relevantes
orientation = info_PET.ImageOrientationPatient; % Dirección de los ejes X y Y
position = info_PET.ImagePositionPatient;       % Posición inicial en LPS
spacing = info_PET.PixelSpacing;                % Espaciado entre píxeles (X, Y)
thickness = info_PET.SliceThickness;            % Espaciado entre cortes (Z)

image=PET(:,:,67); 
% Dimensiones de la imagen
[nRows, nCols] = size(image);

% Calcular las direcciones de los ejes en LPS
x_dir = orientation(1:3); % Dirección del eje X (fila)
y_dir = orientation(4:6); % Dirección del eje Y (columna)
z_dir = cross(x_dir, y_dir); % Dirección del eje Z (normal al plano)

% Generar una cuadrícula de coordenadas en el espacio voxel
[i, j] = ndgrid(0:nRows-1, 0:nCols-1);

% Convertir coordenadas del espacio voxel al sistema LPS
coords_LPS = position(:) + ...
             (spacing(1) * x_dir(:)) * i(:)' + ...
             (spacing(2) * y_dir(:)) * j(:)';

% Extraer las coordenadas X, Y, Z en LPS
X = reshape(coords_LPS(1, :), [nRows, nCols]);
Y = reshape(coords_LPS(2, :), [nRows, nCols]);
Z = reshape(coords_LPS(3, :), [nRows, nCols]); % Z constante para una imagen 2D

% Visualizar la imagen en el sistema de coordenadas LPS
figure;
surf(X, Y, Z, double(image), 'EdgeColor', 'none'); % Mapeo en LPS
colormap gray;
axis equal;
xlabel('X (Izquierda-Derecha)');
ylabel('Y (Posterior-Anterior)');
zlabel('Z (Superior-Inferior)');
title('Imagen en sistema LPS');


% Mostrar el corte transversal en el sistema LPS
figure;
h1=imagesc(image); % Mostrar la imagen
colormap jet;  % Escala de grises
axis equal;     % Mantener la proporción de los píxeles
xlabel('X (Izquierda-Derecha)');  % Eje LPS X
ylabel('Y (Posterior-Anterior)'); % Eje LPS Y
title('Corte transversal en sistema LPS');

% Ajustar las unidades del eje a mm (en lugar de píxeles)
x_mm = (0:size(image, 2)-1) * spacing(1); % Dimensión X (en mm)
y_mm = (0:size(image, 1)-1) * spacing(2); % Dimensión Y (en mm)
set(gca, 'XTick', linspace(1, size(image, 2), 5)); % Escala uniforme
set(gca, 'XTickLabel', linspace(x_mm(1), x_mm(end), 5)); % Etiquetas X en mm
set(gca, 'YTick', linspace(1, size(image, 1), 5)); % Escala uniforme
set(gca, 'YTickLabel', linspace(y_mm(1), y_mm(end), 5)); % Etiquetas Y en mm
colorbar;

%%
orientation = info_CT.ImageOrientationPatient; % Dirección de los ejes X y Y
position = info_CT.ImagePositionPatient;       % Posición inicial en LPS
spacing = info_CT.PixelSpacing;                % Espaciado entre píxeles (X, Y)
thickness = info_CT.SliceThickness;            % Espaciado entre cortes (Z)

image=CT(:,:,67); 

% Mostrar el corte transversal en el sistema LPS
% figure;
hold on 
imagesc(image); % Mostrar la imagen
colormap gray;  % Escala de grises
axis equal;     % Mantener la proporción de los píxeles
xlabel('X (Izquierda-Derecha)');  % Eje LPS X
ylabel('Y (Posterior-Anterior)'); % Eje LPS Y
title('Corte transversal en sistema LPS');

% Ajustar las unidades del eje a mm (en lugar de píxeles)
x_mm = (0:size(image, 2)-1) * spacing(1); % Dimensión X (en mm)
y_mm = (0:size(image, 1)-1) * spacing(2); % Dimensión Y (en mm)
set(gca, 'XTick', linspace(1, size(image, 2), 5)); % Escala uniforme
set(gca, 'XTickLabel', linspace(x_mm(1), x_mm(end), 5)); % Etiquetas X en mm
set(gca, 'YTick', linspace(1, size(image, 1), 5)); % Escala uniforme
set(gca, 'YTickLabel', linspace(y_mm(1), y_mm(end), 5)); % Etiquetas Y en mm
colorbar;
set(h1, 'AlphaData', 0.5); 