close all 
clc 

CT_image=CT; 
PET_image=PET; 

Ref_CT=R_CT; 
Ref_PET=R_PET; 

% Obtener las coordenadas espaciales de cada imagen usando sus referencias
% Para la imagen CT
X_CT = linspace(Ref_CT.XWorldLimits(1), Ref_CT.XWorldLimits(2), Ref_CT.ImageSize(1));
Y_CT = linspace(Ref_CT.YWorldLimits(1), Ref_CT.YWorldLimits(2), Ref_CT.ImageSize(2));
Z_CT = linspace(Ref_CT.ZWorldLimits(1), Ref_CT.ZWorldLimits(2), Ref_CT.ImageSize(3));

% Para la imagen PET
X_PET = linspace(Ref_PET.XWorldLimits(1), Ref_PET.XWorldLimits(2), Ref_PET.ImageSize(1));
Y_PET = linspace(Ref_PET.YWorldLimits(1), Ref_PET.YWorldLimits(2), Ref_PET.ImageSize(2));
Z_PET = linspace(Ref_PET.ZWorldLimits(1), Ref_PET.ZWorldLimits(2), Ref_PET.ImageSize(3));

% Calcular el desplazamiento necesario en X, Y, Z
dx = Ref_CT.XWorldLimits(1) - Ref_PET.XWorldLimits(1);
dy = Ref_CT.YWorldLimits(1) - Ref_PET.YWorldLimits(1);
dz = Ref_CT.ZWorldLimits(1) - Ref_PET.ZWorldLimits(1);

% Calcular el factor de escalado en cada dimensión
scale_x = (Ref_CT.XWorldLimits(2) - Ref_CT.XWorldLimits(1)) / (Ref_PET.XWorldLimits(2) - Ref_PET.XWorldLimits(1));
scale_y = (Ref_CT.YWorldLimits(2) - Ref_CT.YWorldLimits(1)) / (Ref_PET.YWorldLimits(2) - Ref_PET.YWorldLimits(1));
scale_z = (Ref_CT.ZWorldLimits(2) - Ref_CT.ZWorldLimits(1)) / (Ref_PET.ZWorldLimits(2) - Ref_PET.ZWorldLimits(1));

% Reescalar la imagen PET a las dimensiones de la imagen CT
PET_image_rescaled = imresize3(PET_image, [Ref_CT.ImageSize(1), Ref_CT.ImageSize(2), Ref_CT.ImageSize(3)]);

% Mover la imagen PET utilizando el desplazamiento calculado
PET_image_moved = zeros(size(CT_image));  % Crear una imagen de las mismas dimensiones que la CT
for i = 1:Ref_PET.ImageSize(3)
    % Desplazamos la imagen PET en Z, X, Y según el desplazamiento
    if i+dz > 0 && i+dz <= Ref_CT.ImageSize(3)
        PET_image_moved(:,:,i+dz) = PET_image_rescaled(:,:,i);
    end
end
%%
% % Crear una nueva figura para mostrar las imágenes
% figure;
% 
% % Mostrar la imagen CT
% subplot(1,2,1); % Subplot para las imágenes
% imshow(CT_image(:,:,round(Ref_CT.ImageSize(3)/2)), []); % Mostrar el slice medio de la CT
% title('Imagen CT');
% 
% % Mostrar la imagen PET alineada
% subplot(1,2,2); % Subplot para las imágenes
% imshow(PET_image_moved(:,:,round(Ref_CT.ImageSize(3)/2)), []); % Mostrar el slice medio de la PET
% title('Imagen PET alineada');
% %% 
% % Crear una nueva figura para mostrar las imágenes
% figure;
% 
% % Mostrar la imagen CT en el fondo
% imshow(CT_image(:,:,round(Ref_CT.ImageSize(3)/2)), []); % Mostrar el slice medio de la CT
% title('Superposición de PET sobre CT');
% hold on; % Mantener la imagen CT en el fondo
% 
% % Superponer la imagen PET alineada con el colormap 'jet'
% PET_slice = PET_image_moved(:,:,round(Ref_CT.ImageSize(3)/2)); % Slice de la PET alineada
% h = imagesc(PET_slice); % Mostrar la imagen PET
% set(h, 'AlphaData', ~isnan(PET_slice)); % Hacer que la imagen PET tenga transparencia en áreas de fondo
% colormap jet; % Usar el colormap 'jet' para la imagen PET
% colorbar; % Mostrar la barra de colores

%%
% Crear una nueva figura para mostrar las imágenes
figure(500);

% Mostrar la imagen CT en el fondo
imshow(CT_image(:,:,round(Ref_CT.ImageSize(3)/2)), []); % Mostrar el slice medio de la CT
title('Superposición de PET sobre CT');
hold on; % Mantener la imagen CT en el fondo

% Superponer la imagen PET alineada con el colormap 'jet'
PET_slice = PET_image_moved(:,:,round(Ref_CT.ImageSize(3)/2)); % Slice de la PET alineada

% Usar imagesc para la imagen PET sobre la CT
h = imagesc(PET_slice); % Mostrar la imagen PET
set(h, 'AlphaData', ~isnan(PET_slice)); % Hacer que la imagen PET tenga transparencia en áreas de fondo
colormap jet; % Usar el colormap 'jet' para la imagen PET
colorbar; % Mostrar la barra de colores

% Asegurarse de que la imagen PET se muestra encima de la CT
uistack(h, 'top'); % Poner la imagen PET encima de la CT

%% 
% Inicializar la figura y los ejes
nfig = 1; % Asegúrate de que nfig tiene un valor adecuado
figure(nfig);
nfig = nfig + 1;
set(gcf, 'Renderer', 'OpenGL'); % Usar OpenGL para renderizado

% Crear los dos ejes
ax1 = axes; % Eje para la imagen CT
ax2 = axes; % Eje para la imagen PET

% Definir el colormap para las imágenes
gray_colormap = gray;
jet_colormap = jet;
max_PET = max(PET(:)); % Valor máximo de la imagen PET para ajustar la escala de colores

% Recorrer cada slice (corte) de la imagen PET
for nslice = 1:size(PET, 3)
    % Mostrar la imagen CT en el primer eje (ax1)
    imshow(CT(:, :, nslice), [], 'Parent', ax1, 'Colormap', gray_colormap);
    colormap(ax1, gray_colormap); % Asignar colormap gris para CT
    
    % Mostrar la imagen PET en el segundo eje (ax2)
    imshow(PET(:, :, nslice), [], 'Parent', ax2, 'Colormap', jet_colormap);
    colormap(ax2, jet_colormap); % Asignar colormap jet para PET
    
    % Ajustar la escala de colores para la imagen PET y agregar la barra de colores
    clim(ax2, [0 max_PET]); % Ajustar el límite de colores para PET
    colorbar(ax2); % Mostrar barra de colores para PET
    
    % Agregar transparencia a la imagen PET
    alpha(ax2, 0.4); % Ajustar la transparencia de PET
    
    % Copiar la posición del segundo eje (ax2) al primer eje (ax1)
    P = get(ax2, 'Position');
    set(ax1, 'Position', P); % Asegurar que ambos ejes estén en la misma posición
    
    % Agregar título con el número del slice
    h = title(['Fusion CT-PET #', num2str(nslice)]);
    set(h, 'FontWeight', 'bold');
    
    % Pausar para la visualización dinámica
    pause(0.01);
end

%%
% Inicializar la figura y los ejes
nfig = 501; % Asegúrate de que nfig tiene un valor adecuado
figure(nfig);
nfig = nfig + 1;
set(gcf, 'Renderer', 'OpenGL'); % Usar OpenGL para renderizado

% Crear los dos ejes
ax1 = axes; % Eje para la imagen CT
ax2 = axes; % Eje para la imagen PET

% Definir el colormap para las imágenes
gray_colormap = gray;
jet_colormap = jet;
max_PET = max(PET(:)); % Valor máximo de la imagen PET para ajustar la escala de colores

% Recorrer cada slice (corte) de la imagen PET
for nslice = 1:size(PET, 3)
    % Mostrar la imagen CT en el primer eje (ax1)
    imshow(CT(:, :, nslice), [], 'Parent', ax1, 'Colormap', gray_colormap);
    colormap(ax1, gray_colormap); % Asignar colormap gris para CT
    
    % Mostrar la imagen PET en el segundo eje (ax2)
    imshow(PET(:, :, nslice), [], 'Parent', ax2, 'Colormap', jet_colormap);
    colormap(ax2, jet_colormap); % Asignar colormap jet para PET
    
    % Ajustar la escala de colores para la imagen PET y agregar la barra de colores
    clim(ax2, [0 max_PET]); % Ajustar el límite de colores para PET
    colorbar(ax2); % Mostrar barra de colores para PET
    
    % Agregar transparencia a la imagen PET
    alpha(ax2, 0.4); % Ajustar la transparencia de PET
    
    % Copiar la posición del segundo eje (ax2) al primer eje (ax1)
    P = get(ax2, 'Position');
    set(ax1, 'Position', P); % Asegurar que ambos ejes estén en la misma posición
    
    % Agregar título con el número del slice
    h = title(['Fusion CT-PET #', num2str(nslice)]);
    set(h, 'FontWeight', 'bold');
    
    % Pausar para la visualización dinámica
    pause(0.01);
end
%% 
%Ref1_PET=
