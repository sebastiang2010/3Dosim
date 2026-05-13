% Desplazamiento entre las posiciones de origen de PET y CT
dx = ippCT(1) - ippPET(1); % Desplazamiento en X
dy = ippCT(2) - ippPET(2); % Desplazamiento en Y
dz = ippCT(3) - ippPET(3); % Desplazamiento en Z

% Inicializar la imagen PET movida con el tamaño de la imagen CT, llena de NaN o ceros
PET_aligned = NaN(size(CT)); 

% Recorrer la imagen PET y moverla a la imagen CT
for i = 1:size(PET, 3)
    for j = 1:size(PET, 2)
        for k = 1:size(PET, 1)
            % Calcular la nueva posición de cada voxel de PET en las coordenadas de CT
            new_x = round(k + dx / vCT(1));  % Desplazamiento en X según la resolución
            new_y = round(j + dy / vCT(2));  % Desplazamiento en Y según la resolución
            new_z = round(i + dz / vCT(3));  % Desplazamiento en Z según la resolución
            
            % Asegurarse de que la nueva posición esté dentro de los límites de la imagen CT
            if new_x > 0 && new_x <= size(CT, 1) && new_y > 0 && new_y <= size(CT, 2) && new_z > 0 && new_z <= size(CT, 3)
                PET_aligned(new_x, new_y, new_z) = PET(k, j, i);  % Asignar el valor de PET al nuevo lugar en CT
            end
        end
    end
end

% Visualización superpuesta de las imágenes PET y CT usando un bucle 'for'
figure;

% Recorrer los slices de la imagen
for nslice = 1:size(PET, 3)
    % Mostrar la imagen CT
    imshow(CT(:, :, nslice), [], 'Colormap', gray);
    hold on;  % Mantener la imagen CT para superponer la imagen PET
    % Superponer la imagen PET alineada con transparencia
    PET_slice = PET_aligned(:, :, nslice);  % Slice de la imagen PET alineada
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



