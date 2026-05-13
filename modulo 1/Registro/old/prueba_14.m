clc;
close all;

% Asumimos que ya tienes la variable PET con la imagen 3D cargada
% También asumimos que tienes la referencia R_PET definida, que nos proporciona las coordenadas físicas

% Obtener las dimensiones del volumen (nI, nJ, nK son las dimensiones del volumen en 3D)
[nI, nJ, nK] = size(PET);

% Definir el espacio 3D del volumen con las coordenadas físicas
[X, Y, Z] = meshgrid(1:nI, 1:nJ, 1:nK);

% Ajustar las coordenadas físicas según el sistema de referencia (LPS o RAS)
X_phys = R_PET.XWorldLimits(1) + (X - 1) * vPET(1);
Y_phys = R_PET.YWorldLimits(1) + (Y - 1) * vPET(2);
Z_phys = R_PET.ZWorldLimits(1) + (Z - 1) * vPET(3);

% Definir el índice de corte en Z (el corte se hace en un valor constante de Z)
slice_index =120 ;  % Cambia este valor según el corte que quieras ver

% Seleccionar el corte que queremos mostrar en el plano Z (trasversal).
% En el plano XY, para un valor de Z determinado, mostramos todos los puntos en X e Y.
% Esto se hace usando slice:
figure;
slice(X_phys, Y_phys, Z_phys, PET, [], [], slice_index);  % Corte transversal en Z = slice_index

% Ajustar la visualización para hacerla más clara
colormap('jet');    % Usamos el mapa de colores en escala de grises
colorbar;            % Agregamos la barra de color
xlabel('Coordenada X (mm)');   % Etiqueta del eje X
ylabel('Coordenada Y (mm)');   % Etiqueta del eje Y
zlabel('Coordenada Z (mm)');   % Etiqueta del eje Z
title(['Corte transversal en el plano XY en Z = ', num2str(slice_index)]);   % Título con la posición del corte
axis equal;  % Asegura que las escalas en los ejes sean iguales
view(2)

%% 
[nI, nJ, nK] = size(CT);

CT=double(CT); 
a=CT; 
a=a./max(a(:)); 

% Definir el espacio 3D del volumen con las coordenadas físicas
[X, Y, Z] = meshgrid(1:nI, 1:nJ, 1:nK);

% Ajustar las coordenadas físicas según el sistema de referencia (LPS o RAS)
X_phys = R_CT.XWorldLimits(1) + (X - 1) * vCT(1);
Y_phys = R_CT.YWorldLimits(1) + (Y - 1) * vCT(2);
Z_phys = R_CT.ZWorldLimits(1) + (Z - 1) * vCT(3);

% Definir el índice de corte en Z (el corte se hace en un valor constante de Z)
slice_index =120 ;  % Cambia este valor según el corte que quieras ver

% Seleccionar el corte que queremos mostrar en el plano Z (trasversal).
% En el plano XY, para un valor de Z determinado, mostramos todos los puntos en X e Y.
% Esto se hace usando slice:
figure;
slice(X_phys, Y_phys, Z_phys, a, [], [], 120);  % Corte transversal en Z = slice_index

% Ajustar la visualización para hacerla más clara
colormap('gray');    % Usamos el mapa de colores en escala de grises
colorbar;            % Agregamos la barra de color
xlabel('Coordenada X (mm)');   % Etiqueta del eje X
ylabel('Coordenada Y (mm)');   % Etiqueta del eje Y
zlabel('Coordenada Z (mm)');   % Etiqueta del eje Z
title(['Corte transversal en el plano XY en Z = ', num2str(slice_index)]);   % Título con la posición del corte
axis equal;  % Asegura que las escalas en los ejes sean iguales
view(2)
clim([0 1]);

%%
clc;
close all;

% Cargar imágenes (PET y CT)
PET = paciente.PET_original;
CT = paciente.CT;

% Obtener la información de los DICOM
info_PET = paciente.info_PET;
info_CT = paciente.info_CT;

% Definir las dimensiones físicas de cada imagen (según los metadatos DICOM)
vPET = [4.07, 4.07, 2];  % Voxels por unidad (PET)
vCT = [0.8, 0.8, 2];     % Voxels por unidad (CT)

% Las posiciones y orientaciones en LPS o RAS
orientationPET = info_PET.ImageOrientationPatient; 
ippPET = info_PET.ImagePositionPatient; 
orientationCT = info_CT.ImageOrientationPatient; 
ippCT = info_CT.ImagePositionPatient; 

% Crear las referencias espaciales 3D
R_PET = imref3d(size(PET), [ippPET(1), ippPET(1)+vPET(1)*size(PET,1)], ...
                           [ippPET(2), ippPET(2)+vPET(2)*size(PET,2)], ...
                           [ippPET(3), ippPET(3)+vPET(3)*size(PET,3)]);

R_CT = imref3d(size(CT), [ippCT(1), ippCT(1)+vCT(1)*size(CT,1)], ...
                          [ippCT(2), ippCT(2)+vCT(2)*size(CT,2)], ...
                          [ippCT(3), ippCT(3)+vCT(3)*size(CT,3)]);

% Normalizar las imágenes PET y CT
PET = double(PET) / max(PET(:));  % Normalizar PET
CT = double(CT);
window_min = -1000;   % Rango de ventana para CT
window_max = 2000;
CT = (CT - window_min) / (window_max - window_min); % Normalizar CT

% Crear el volumen de corte en el eje Z
nI = size(CT, 1);  % Dimensiones de la imagen
nJ = size(CT, 2);
nK = size(CT, 3);

[X, Y, Z] = meshgrid(1:nI, 1:nJ, 1:nK);

% Coordenadas físicas para CT
X_phys_CT = R_CT.XWorldLimits(1) + (X - 1) * vCT(1);
Y_phys_CT = R_CT.YWorldLimits(1) + (Y - 1) * vCT(2);
Z_phys_CT = R_CT.ZWorldLimits(1) + (Z - 1) * vCT(3);

% Coordenadas físicas para PET
X_phys_PET = R_PET.XWorldLimits(1) + (X - 1) * vPET(1);
Y_phys_PET = R_PET.YWorldLimits(1) + (Y - 1) * vPET(2);
Z_phys_PET = R_PET.ZWorldLimits(1) + (Z - 1) * vPET(3);

% Seleccionar un corte transversal (en Z, por ejemplo)
slice_index = 120;  % Corte en Z (puedes ajustar según lo que necesites)

% Crear la figura para superponer las imágenes
figure;

% Mostrar el corte de la imagen PET
hold on;
slice(X_phys_PET, Y_phys_PET, Z_phys_PET, PET, [], [], slice_index); % Corte de PET
colormap('jet');  % Colores para PET
alpha(0.5);  % Hacer la imagen PET semi-transparente para ver la CT debajo

% Mostrar el corte de la imagen CT
slice(X_phys_CT, Y_phys_CT, Z_phys_CT, CT, [], [], slice_index); % Corte de CT
colormap('gray');  % Colores para CT
alpha(0.5);  % Hacer la imagen CT semi-transparente

% Ajustar la visualización
colorbar;            % Barra de color
title(['Superposición de PET y CT en el corte Z = ', num2str(slice_index)]);
xlabel('Coordenada X (mm)');
ylabel('Coordenada Y (mm)');
zlabel('Coordenada Z (mm)');
axis equal;          % Asegura que las escalas en los ejes sean iguales
view(2);             % Vista en 2D (plano XY)
hold off;



