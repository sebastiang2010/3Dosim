clc 
close all 
%% 
R_PET=imref3d(size(PET),[ippPET(1) ippPET(1)+vPET(1)*size(PET,1)],[ippPET(2) ippPET(2)+vPET(2)*size(PET,2)],[ippPET(3) ippPET(3)+vPET(3)*size(PET,3)]);
R_CT=imref3d(size(CT),[ippCT(1) ippCT(1)+vCT(1)*size(CT,1)],[ippCT(2) ippCT(2)+vCT(2)*size(CT,2)],[ippCT(3) ippCT(3)+vCT(3)*size(CT,3)]);
%% 
%close all 
a=double(CT(:,:,20));
R_CT2=imref2d(size(a),[ippCT(1) ippCT(1)+vCT(1)*size(CT,1)],[ippCT(2) ippCT(2)+vCT(2)*size(CT,2)]);
b=double(PET(:,:,20));
R_PET2=imref2d(size(b),[ippPET(1), ippPET(1)+vPET(1)*size(PET,1)],[ippPET(2), ippPET(2)+vPET(2)*size(PET,2)]);



% Crear una figura nueva
figure(100)
ax1 = axes;
imshow(a ./ max(a(:)), R_CT2, 'Parent', ax1);  
hold on
ax2 = axes;
h = imshow(b ./ max(b(:)), R_PET2, 'Parent', ax2);  % Mostrar PET en su sistema de referencia
set(ax2, 'Color', 'none');  % Hacer transparente el fondo de ax2
set(h, 'AlphaData', 0.5);  % Ajustar transparencia de la imagen PET
colormap(ax2, jet);
colorbar(ax2);  % Agregar una barra de color solo para la imagen PET (opcional)
linkaxes([ax1, ax2],'xy');
axis(ax1, 'off');   % Mostrar ejes si quieres visualizar las coordenadas
%%






%% Acomodo en la nueva posicion 
% Desplazamiento entre las posiciones de origen de PET y CT
dx = ippCT(1) - ippPET(1);  % Desplazamiento en X
dy = ippCT(2) - ippPET(2);  % Desplazamiento en Y
dz = ippCT(3) - ippPET(3);  % Desplazamiento en Z

%des_x=R_PET.XWorldLimits(1)+dx; 
%des_y=R_PET.YWorldLimits(1)+dy; 
%des_z=R_PET.ZWorldLimits(1)+dz; 

% % Crear la matriz de transformación de traslación
% tform = affine3d([1 0 0 0; 
%                   0 1 0 0; 
%                   0 0 1 0; 
%                   des_x des_y des_z 1]);

tform = affine3d([1 0 0 0; 
                  0 1 0 0; 
                  0 0 1 0; 
                  1 1 1 1]);


a1=R_CT.XWorldLimits(1);  
a2=a1+R_PET.ImageExtentInWorldX; 
b1=R_CT.YWorldLimits(1); 
b2=b1+R_PET.ImageExtentInWorldY; 
c1=R_CT.ZWorldLimits(1); 
c2=c1+R_PET.ImageExtentInWorldZ; 
 
R_PET_moved=imref3d(size(PET),[a1 a2], [b1 b2], [c1 c2]); 


R_PET2_moved=imref2d(size(PET),R_PET_moved.XWorldLimits,R_PET_moved.YWorldLimits); 
%R2_CT=imref2d(size(CT),R_CT.XWorldLimits,R_CT.YWorldLimits); 


normalized_image = rescale(CT(:,:,60));

figure(101)
ax1 = axes;
imshow(a ./ max(a(:)), R_CT2, 'Parent', ax1);  
hold on
ax2 = axes;
h = imshow(b ./ max(b(:)), R_PET2_moved, 'Parent', ax2);  % Mostrar PET en su sistema de referencia
set(ax2, 'Color', 'none');  % Hacer transparente el fondo de ax2
set(h, 'AlphaData', 0.5);  % Ajustar transparencia de la imagen PET
colormap(ax2, jet);
colorbar(ax2);  % Agregar una barra de color solo para la imagen PET (opcional)
linkaxes([ax1, ax2],'xy');
axis(ax1, 'off');   % Mostrar ejes si quieres visualizar las coordenadas


%% 
z_CT = R_CT.ZWorldLimits(1) + (60 - 1) * R_CT.PixelExtentInWorldZ;













