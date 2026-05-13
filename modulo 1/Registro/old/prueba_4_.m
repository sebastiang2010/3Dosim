% Desplazamiento entre las posiciones de origen de PET y CT
dx = ippCT(1) - ippPET(1); % Desplazamiento en X
dy = ippCT(2) - ippPET(2); % Desplazamiento en Y
dz = ippCT(3) - ippPET(3); % Desplazamiento en Z

% Crear la matriz de transformación de traslación (matriz 3x3 para afín)
tranf = affine3d([1 0 0 0; 0 1 0 0; 0 0 1 0; dx dy dz 1]);

% Crear una referencia espacial para la imagen CT
R_CT = imref3d(size(CT), [ippCT(1) ippCT(1) + vCT(1) * size(CT,1)], ...
                 [ippCT(2) ippCT(2) + vCT(2) * size(CT,2)], ...
                 [ippCT(3) ippCT(3) + vCT(3) * size(CT,3)]);

% Mover la imagen PET con la transformación
%PET_moved = imwarp(PET, tform, 'OutputView', R_CT);
[PET_moved,R_PET1]=imwarp(PET,R_PET,tranf,interp);%,'OutputView',imref3d(size(PET)));
% Visualización de las imágenes PET movida y CT superpuestas usando un bucle 'for'
figure;

% Recorrer los slices de la imagen
for nslice = 1:size(PET, 3)
    % Mostrar la imagen CT
    imshow(CT(:, :, nslice), [], 'Colormap', gray);
    hold on;  % Mantener la imagen CT para superponer la imagen PET
    % Superponer la imagen PET movida con transparencia
    PET_slice = PET_moved(:, :, nslice);  % Slice de la imagen PET movida
    h = imagesc(PET_slice);  % Mostrar la imagen PET sobre la CT
    set(h, 'AlphaData', ~isnan(PET_slice));  % Hacer que la imagen PET tenga transparencia en áreas de fondo
    colormap jet;  % Usar el colormap 'jet' para la imagen PET
    colorbar;  % Mostrar la barra de colores para PET
    
    % Agregar título con el número del slice
    title(['Superposición de PET sobre CT - Slice ', num2str(nslice)]);
    
    % Pausar para la visualización dinámica
    pause(0.1);  % Puedes ajustar el tiempo de pausa según necesites
    
    hold off;  % Liberar la imagen CT para el siguiente slice
end




