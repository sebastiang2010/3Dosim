% Limpiar el entorno
clc;

% Definir las imágenes y sus referencias
CT_image = CT;
PET_image = PET;

Ref_CT = R_CT;  % Referencia de la imagen CT
Ref_PET = R_PET; % Referencia de la imagen PET

% Obtener las coordenadas espaciales de cada imagen usando sus referencias
X_CT = linspace(Ref_CT.XWorldLimits(1), Ref_CT.XWorldLimits(2), Ref_CT.ImageSize(1));
Y_CT = linspace(Ref_CT.YWorldLimits(1), Ref_CT.YWorldLimits(2), Ref_CT.ImageSize(2));
Z_CT = linspace(Ref_CT.ZWorldLimits(1), Ref_CT.ZWorldLimits(2), Ref_CT.ImageSize(3));

X_PET = linspace(Ref_PET.XWorldLimits(1), Ref_PET.XWorldLimits(2), Ref_PET.ImageSize(1));
Y_PET = linspace(Ref_PET.YWorldLimits(1), Ref_PET.YWorldLimits(2), Ref_PET.ImageSize(2));
Z_PET = linspace(Ref_PET.ZWorldLimits(1), Ref_PET.ZWorldLimits(2), Ref_PET.ImageSize(3));

% Calcular el desplazamiento necesario en X, Y, Z
dx = round((Ref_CT.XWorldLimits(1) - Ref_PET.XWorldLimits(1)) / (X_CT(2) - X_CT(1))); % Desplazamiento en X
dy = round((Ref_CT.YWorldLimits(1) - Ref_PET.YWorldLimits(1)) / (Y_CT(2) - Y_CT(1))); % Desplazamiento en Y
dz = round((Ref_CT.ZWorldLimits(1) - Ref_PET.ZWorldLimits(1)) / (Z_CT(2) - Z_CT(1))); % Desplazamiento en Z

% Crear una imagen de NaN de las mismas dimensiones que la imagen CT
PET_image_moved = NaN(size(CT_image));  % Inicializa con NaN para llenar el espacio vacío

% Mover la imagen PET sin interpolación
for i = 1:Ref_PET.ImageSize(3)
    % Calcular el índice en Z para la imagen PET
    new_z = i + dz;
    
    % Verificar si el índice está dentro de los límites de la imagen CT
    if new_z > 0 && new_z <= Ref_CT.ImageSize(3)
        % Asegurarse de que el índice está dentro de los límites de la imagen CT
        % Redimensionar la imagen PET para ajustarse a las dimensiones de CT
        x_start = max(1, 1 + dx); % Indice de inicio en X
        x_end = min(size(CT_image,1), size(PET_image,1) + dx); % Indice de fin en X
        y_start = max(1, 1 + dy); % Indice de inicio en Y
        y_end = min(size(CT_image,2), size(PET_image,2) + dy); % Indice de fin en Y

        % Asignar la parte de la imagen PET movida a la imagen CT
        PET_image_moved(x_start:x_end, y_start:y_end, new_z) = PET_image(:,:,i);
    end
end

% Mostrar las imágenes
figure(500);

% Mostrar la imagen CT en el fondo
imshow(CT_image(:,:,round(Ref_CT.ImageSize(3)/2)), []); % Mostrar el slice medio de la CT
title('Superposición de PET sobre CT');
hold on;

% Superponer la imagen PET alineada con el colormap 'jet'
PET_slice = PET_image_moved(:,:,round(Ref_CT.ImageSize(3)/2)); % Slice de la PET alineada

% Usar imagesc para la imagen PET sobre la CT
h = imagesc(PET_slice); % Mostrar la imagen PET
set(h, 'AlphaData', ~isnan(PET_slice)); % Hacer que la imagen PET tenga transparencia en áreas de fondo
colormap jet; % Usar el colormap 'jet' para la imagen PET
colorbar; % Mostrar la barra de colores

% Asegurarse de que la imagen PET se muestra encima de la CT
uistack(h, 'top'); % Poner la imagen PET encima de la CT

% Ajustar la transparencia de la imagen PET si es necesario
alpha(h, 0.4);  % Ajustar la transparencia de PET según el valor deseado


