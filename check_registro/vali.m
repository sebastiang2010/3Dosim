%% Configuración inicial
clear; clc; close all;

% Tamaño de la imagen (filas, columnas, slices)
s = [100, 100, 20]; 

% Definir índices de Hounsfield (HU)
index.aire = -1000;
index.hueso = 1000;
index.higado = 60;

%% Generar CT sintético
CT = ones(s) * index.aire; 
CT(40:60, 30:50, 5:15) = index.higado; % Hígado (cubo 20x20x10)
CT(70:80, 10:20, 5:15) = index.hueso;  % Hueso (cubo pequeño)

% Visualizar CT (slice central)
figure;
imshow(CT(:,:,10), [index.aire index.hueso]);
colormap(gray); title('CT Sintético (Slice 10)');

%% Generar PET sintético (actividad solo en el hígado)
PET = zeros(s);
PET(40:60, 30:50, 5:15) = 1; % Actividad = 1 Bq/vóxel

% Desplazar PET 15 voxels en X (simular mala alineación)
PET_desplazado = zeros(s);
PET_desplazado(40:60, 45:65, 5:15) = 1; % PET desplazado

% Visualizar PET desplazado vs CT
figure;
imshow(CT(:,:,10), [index.aire index.hueso]); 
hold on;
h = imshow(PET_desplazado(:,:,10), []);
set(h, 'AlphaData', 0.3);
colormap(jet); title('PET Desplazado vs CT (Slice 10)');