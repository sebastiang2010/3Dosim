% Desplazamiento entre las posiciones de origen de PET y CT
dx = ippCT(1) - ippPET(1); % Desplazamiento en X
dy = ippCT(2) - ippPET(2); % Desplazamiento en Y
dz = ippCT(3) - ippPET(3); % Desplazamiento en Z

% Crear la matriz de transformación de traslación (matriz 3x3 para afín)
tform = affine3d([1 0 0 0; 0 1 0 0; 0 0 1 0; dx dy dz 1]);

% Crear una imagen PET nueva de tamaño 512x512xN (tamaño de la imagen CT) con NaNs
PET_moved = NaN(size(CT));

% Crear una referencia espacial para la imagen CT
R_CT = imref3d(size(CT), [ippCT(1) ippCT(1) + vCT(1) * size(CT,1)], ...
                 [ippCT(2) ippCT(2) + vCT(2) * size(CT,2)], ...
                 [ippCT(3) ippCT(3) + vCT(3) * size(CT,3)]);

% Mover la imagen PET con la transformación
[PET_moved, R_PET1] = imwarp(PET, R_PET, tform, 'OutputView', R_CT, 'Interpolation', 'linear');

% Visualización de las imágenes PET movida y CT superpuestas usando un bucle 'for'
figure;

% Recorrer los slices de la imagen
for nslice = 1:size(CT, 3)
    % Crear una referencia 2D para la imagen CT en este slice
    R_CT_2D = imref2d(size(CT(:, :, nslice)), ...
                       [ippCT(1) ippCT(1) + vCT(1) * size(CT,1)], ...
                       [ippCT(2) ippCT(2) + vCT(2) * size(CT,2)]);

    % Mostrar la imagen CT con la referencia espacial 2D
    imshow(CT(:, :, nslice), [], 'Colormap', gray, 'InitialMagnification', 'fit', 'YData', [ippCT(1) ippCT(1) + vCT(1) * size(CT,1)], 'XData', [ippCT(2) ippCT(2) + vCT(2) * size(CT,2)]);
    hold on;  % Mantener la imagen CT para superponer la imagen PET
    
    % Superponer la imagen PET movida con transparencia
    PET_slice = PET_moved(:, :, nslice);  % Slice de la imagen PET movida
    imshow(PET_slice, [], 'Colormap', jet, 'InitialMagnification', 'fit', 'AlphaData', ~isnan(PET_slice)); % Transparencia con NaN
    
    % Colormap para PET y barra de colores
    colorbar;
    
    % Agregar título con el número del slice
    title(['Superposición de PET sobre CT - Slice ', num2str(nslice)]);
    
    % Pausar para la visualización dinámica
    pause(0.1);
    
    hold off;  % Liberar la imagen CT para el siguiente slice
end





