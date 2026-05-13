clear 
clc 
close all 
clear 

load('C:\MAT\3Dosim\paciente.mat')

info_PET=paciente.info_PET; 
info_CT=paciente.info_CT; 
PET=paciente.PET; 
CT=paciente.CT; 
vPET=paciente.vPET; 
vCT=paciente.vCT; 

ippCT=info_CT.ImagePositionPatient; 
ippPET=info_PET.ImagePositionPatient; 
orientation_CT=info_CT.ImageOrientationPatient; 
orientation_PET=info_PET.ImageOrientationPatient; 


%% LPS?
LPS_CT=false; 
LPS_PET=false; 

x_dir = orientation_PET(1:3); % Dirección del eje X
y_dir = orientation_PET(4:6); % Dirección del eje Y

% En LPS: X (Izquierda-Derecha), Y (Posterior-Anterior), Z (Superior-Inferior)
% En RAS: X (Derecha-Izquierda), Y (Anterior-Posterior), Z (Superior-Inferior)
if x_dir(1) >= 0 
    if y_dir(2) >= 0 
        LPS_PET=true; 
    end 
end 

x_dir = orientation_CT(1:3); % Dirección del eje X
y_dir = orientation_CT(4:6); % Dirección del eje Y
if x_dir(1) >= 0
    if y_dir(2) >= 0
       LSP_CT=true;
    end 
end 
%%
R_PET=imref3d(size(PET),[ippPET(1) ippPET(1)+vPET(1)*size(PET,1)],[ippPET(2) ippPET(2)+vPET(2)*size(PET,2)],[ippPET(3) ippPET(3)+vPET(3)*size(PET,3)]);
R_CT=imref3d(size(CT),[ippCT(1) ippCT(1)+vCT(1)*size(CT,1)],[ippCT(2) ippCT(2)+vCT(2)*size(CT,2)],[ippCT(3) ippCT(3)+vCT(3)*size(CT,3)]);
%% 
indice=20; 

a=double(CT(:,:,indice));
b=double(PET(:,:,indice));

R_CT2=imref2d(size(a),[ippCT(1) ippCT(1)+vCT(1)*size(CT,1)],[ippCT(2) ippCT(2)+vCT(2)*size(CT,2)]);
R_PET2=imref2d(size(b),[ippPET(1), ippPET(1)+vPET(1)*size(PET,1)],[ippPET(2), ippPET(2)+vPET(2)*size(PET,2)]);

max1=max(PET(:)); 


% Crear una figura nueva
figure(100)
ax1 = axes;
imshow(a ./ max(a(:)), R_CT2, 'Parent', ax1);  
hold on
ax2 = axes;
h = imshow(b, R_PET2, 'Parent', ax2);  % Mostrar PET en su sistema de referencia
set(ax2, 'Color', 'none');  % Hacer transparente el fondo de ax2
set(h, 'AlphaData', 0.5);  % Ajustar transparencia de la imagen PET
colormap(ax2, jet);
colorbar(ax2);  % Agregar una barra de color solo para la imagen PET (opcional)
%linkaxes([ax1, ax2],'xy');
axis(ax1, 'off');   % Mostrar ejes si quieres visualizar las coordenadas
clim([0 max1])
%%
sPET=size(PET); 
sCT=size(CT); 
PET_show=zeros(sPET(1),sPET(2),sCT(3));
PET_show(1:end,1:end,1:sPET(3))=PET; 
%%
% figure(101)
% for nslice=1:sCT(3)
%     cla
%     clf 
%     a=double(CT(:,:,nslice));
%     b=PET_show(:,:,nslice);
%     ax1 = axes;
%     imshow(a ./ max(a(:)), R_CT2, 'Parent', ax1);
%     hold on
%     ax2 = axes;
%     h = imshow(b, R_PET2, 'Parent', ax2);  % Mostrar PET en su sistema de referencia
%     set(ax2, 'Color', 'none');  % Hacer transparente el fondo de ax2
%     set(h, 'AlphaData', 0.5);  % Ajustar transparencia de la imagen PET
%     colormap(ax2, jet);
%     colorbar(ax2);  % Agregar una barra de color solo para la imagen PET (opcional)
%     %linkaxes([ax1, ax2],'xy');
%     axis(ax1, 'off');
%     axis(ax2,'off')% Mostrar ejes si quieres visualizar las coordenadas
%     clim([0 max1])
%     txt=[' Slice N : ',num2str(nslice)]; 
%     title(txt)
%     pause(0.1)
% 
% end
%% 
% figure(102)
% for nslice = 1:sCT(3)
%     clf
%     a = double(CT(:,:,nslice));
%     b = double(PET_show(:,:,nslice));
% 
%     % Crear subplot para la imagen CT (en el primer subplot)
%     ax1 = axes('Position', [0.1, 0.1, 0.4, 0.8]);
%     h=subplot(1, 2, 1);
%     imshow(a ./ max(a(:)), R_CT2);  % Mostrar CT en su sistema de referencia
%     %axis off;  % Apagar los ejes
%     title(['CT Slice N: ', num2str(nslice)]);  % Título para la imagen CT
%     colormap(h,'gray') 
% 
%     % Crear subplot para la imagen PET (en el segundo subplot)
% 
%     h1=subplot(1, 2, 2);
%     h = imshow(b, R_PET2);  % Mostrar PET en su sistema de referencia
%     %set(h, 'AlphaData', 0.5);  % Ajustar transparencia de la imagen PET
%     colormap(h1, jet);  % Colormap para la imagen PET
%     colorbar(h1);  % Agregar una barra de color solo para la imagen PET (opcional)
%     %axis off;  % Apagar los ejes
%     title(['PET Slice N: ', num2str(nslice)]);  % Título para la imagen PET
%     clim([0 max1])
% 
%     pause(0.5);  % Pausar para visualizar la siguiente imagen
% end
%% traslado la CT 
posfinal=[0 0 0]; 
desp(1)=posfinal(1)-R_CT.XWorldLimits(1); 
desp(2)=posfinal(2)-R_CT.YWorldLimits(1);
desp(3)=posfinal(3)-R_CT.ZWorldLimits(1);  


T=affine3d([1 0 0 0; 
            0 1 0 0; 
            0 0 1 0; 
            desp(1) desp(2) desp(3) 1]);

[CT_moved,R_CT_moved]=imwarp(CT,R_CT,T); %,interp);
[PET_moved,R_PET_moved]=imwarp(PET,R_PET,T); %,interp);
%%
R_PET2=imref2d(size(PET),R_PET_moved.XWorldLimits,R_PET_moved.YWorldLimits);
R_CT2=imref2d(size(CT),R_CT_moved.XWorldLimits,R_CT_moved.YWorldLimits);


% figure(200)
% for nslice=1:sCT(3)
%     cla
%     clf 
%     a=double(CT(:,:,nslice));
%     b=PET_show(:,:,nslice);
%     ax1 = axes;
%     imshow(a ./ max(a(:)), R_CT2, 'Parent', ax1);
%     hold on
%     ax2 = axes;
%     h = imshow(b, R_PET2, 'Parent', ax2);  % Mostrar PET en su sistema de referencia
%     set(ax2, 'Color', 'none');  % Hacer transparente el fondo de ax2
%     set(h, 'AlphaData', 0.5);  % Ajustar transparencia de la imagen PET
%     colormap(ax2, jet);
%     colorbar(ax2);  % Agregar una barra de color solo para la imagen PET (opcional)
%     %linkaxes([ax1, ax2],'xy');
%     axis(ax1, 'off');
%     axis(ax2,'off')% Mostrar ejes si quieres visualizar las coordenadas
%     clim([0 max1])
%     txt=[' Slice N : ',num2str(nslice)]; 
%     title(txt)
%     pause(0.1)
% 
% end




%%
[X, Y, Z] = meshgrid(1:sCT(1), 1:sCT(2), 1:sCT(3));
% Coordenadas físicas para CT
X_phys_CT = R_CT_moved.XWorldLimits(1) + (X - 1) * vCT(1);
Y_phys_CT = R_CT_moved.YWorldLimits(1) + (Y - 1) * vCT(2);
Z_phys_CT = R_CT_moved.ZWorldLimits(1) + (Z - 1) * vCT(3);

[X1, Y1, Z1] = meshgrid(1:sPET(1), 1:sPET(2), 1:sPET(3));
% Coordenadas físicas para PET
X_phys_PET = R_PET_moved.XWorldLimits(1) + (X1 - 1) * vPET(1);
Y_phys_PET = R_PET_moved.YWorldLimits(1) + (Y1 - 1) * vPET(2);
Z_phys_PET = R_PET_moved.ZWorldLimits(1) + (Z1 - 1) * vPET(3);


%% ejempplo 
ijk=[10,20,30]; 
% posx=X_phys_PET(ijk(1),ijk(2),ijk(3)); 
% posy=Y_phys_PET(ijk(1),ijk(2),ijk(3)); 
% posz=Z_phys_PET(ijk(1),ijk(2),ijk(3));
% 
% pos=[posx,posy,posz]; 
%pos = [X_phys_PET(ijk(1), ijk(2), ijk(3)), ...
%       Y_phys_PET(ijk(1), ijk(2), ijk(3)), ...
%       Z_phys_PET(ijk(1), ijk(2), ijk(3))];


%% quiero lo que esta dentro de CT  
R_PET=R_PET_moved; 
R_CT=R_CT_moved; 

corteN=100; 

[ind_1]=find(PET(:,:,:)>=corteN); %actividad
[x,y,z]=ind2sub([sPET(1),sPET(2),sPET(3)],ind_1);

pos(:,1) = R_PET.XWorldLimits(1) + (x - 1) * vPET(1);
pos(:,2) = R_PET.YWorldLimits(1) + (y - 1) * vPET(2);
pos(:,3) = R_PET.ZWorldLimits(1) + (z - 1) * vPET(3);

 a1=pos(:,1)>R_CT.XWorldLimits(1)  ;
 a2=pos(:,1)<R_CT.XWorldLimits(2) ;    
 a3 = a1+a2;    
 b1=a3==2; 
 clear a1 a2 a3    
 a1=pos(:,2)>R_CT.YWorldLimits(1)  ;
 a2=pos(:,2)<R_CT.YWorldLimits(2) ;    
 a3 = a1+a2;    
 b2=a3==2; 
 clear a1 a2 a3    
 a1=pos(:,3)>R_CT.ZWorldLimits(1)  ;
 a2=pos(:,3)<R_CT.ZWorldLimits(2) ;    
 a3 = a1+a2;    
 b3=a3==2; 
 clear a1 a2 a3 
 c=b1+b2+b3; 
 %ind=[]; 
 d=c==3; 
 clear c  

 ind_2=find(d==1); 

 pos1=pos(ind_2,:); 

 x=(pos1(:,1)-R_PET.XWorldLimits(1))./vPET(1); 
 x=x+1; 
 y=(pos1(:,2)-R_PET.YWorldLimits(1))./vPET(2); 
 y=y+1;
 z=(pos1(:,3)-R_PET.ZWorldLimits(1))./vPET(3); 
 z=z+1;

 ind_3=sub2ind(size(PET),x,y,z);
 
 p=PET(ind_3); 





