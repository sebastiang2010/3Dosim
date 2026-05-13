% Cargar las imágenes (ajustar si es necesario)


% Crear un grid de coordenadas en el espacio físico
[XCT, YCT, ZCT] = ndgrid(linspace(Ref_CT.XWorldLimits(1), Ref_CT.XWorldLimits(2), Ref_CT.ImageSize(1)), ...
                          linspace(Ref_CT.YWorldLimits(1), Ref_CT.YWorldLimits(2), Ref_CT.ImageSize(2)), ...
                          linspace(Ref_CT.ZWorldLimits(1), Ref_CT.ZWorldLimits(2), Ref_CT.ImageSize(3)));

[XPET, YPET, ZPET] = ndgrid(linspace(Ref_PET.XWorldLimits(1), Ref_PET.XWorldLimits(2), Ref_PET.ImageSize(1)), ...
                            linspace(Ref_PET.YWorldLimits(1), Ref_PET.YWorldLimits(2), Ref_PET.ImageSize(2)), ...
                            linspace(Ref_PET.ZWorldLimits(1), Ref_PET.ZWorldLimits(2), Ref_PET.ImageSize(3)));

% Interpolar la imagen PET a la resolución de la imagen CT
PET_image_interpolated = interp3(XPET, YPET, ZPET, PET_image, XCT, YCT, ZCT, 'linear', 0);

% Mostrar las imágenes superpuestas en Z (tomando slices en Z)
z_slice = 80; % Seleccionar un slice específico, por ejemplo, el slice Z = 80
CT_slice = CT_image(:, :, z_slice);
PET_slice = PET_image_interpolated(:, :, z_slice);

% Graficar la superposición
figure;
hold on;
imagesc(CT_slice);
colormap gray;
alpha(0.5); % Transparencia de la imagen CT
h = imagesc(PET_slice);
colormap jet;
alpha(0.7); % Transparencia de la imagen PET
hold off;
colorbar;
axis equal;
title('Superposición de CT y PET');
