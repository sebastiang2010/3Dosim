clear 
clc 
close all 
clear 

file_paciente='C:\MAT\3Dosim\paciente.mat'; 
load(file_paciente)

nslice=85; 
nfig=1; 

%
%interpolacion{1,1}='linear';
%interpolacion{1,2}='nearest'; 
%interpolacion{1,3}='cubic'; 
%interpolacion{1,4}='makima';
%interpolacion{1,5}='spline'; 
type_intp=2; 

%
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

sCT=size(CT); 
sPET=size(PET);

%%
%A=[]; 
A=double(PET); 
Actividad=sum(A(:));
Actividad_GBq_org=Actividad/1e9; 

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

a=double(CT(:,:,nslice));
b=double(PET(:,:,nslice));

R_CT2=imref2d(size(a),[ippCT(1) ippCT(1)+vCT(1)*size(CT,1)],[ippCT(2) ippCT(2)+vCT(2)*size(CT,2)]);
R_PET2=imref2d(size(b),[ippPET(1), ippPET(1)+vPET(1)*size(PET,1)],[ippPET(2), ippPET(2)+vPET(2)*size(PET,2)]);

max1=max(PET(:)); 

%% 
% Crear una figura nueva
figure(nfig)
nfig=nfig+1; 
ax1 = axes;
imshow(a ./ max(a(:)), R_CT2, 'Parent', ax1);  

figure(nfig)
nfig=nfig+1; 
ax1 = axes;
h = imshow(b, R_PET2, 'Parent', ax1);  
colormap(ax1, jet);
colorbar(ax1); 
clim([0 max1])

%% traslado la CT 
posfinal=[0 0 0]; 
desp(1)=posfinal(1)-R_CT.XWorldLimits(1); 
desp(2)=posfinal(2)-R_CT.YWorldLimits(1);
desp(3)=posfinal(3)-R_CT.ZWorldLimits(1);  


T=affine3d([1 0 0 0; 
            0 1 0 0; 
            0 0 1 0; 
            desp(1) desp(2) desp(3) 1]);

[CT_moved,R_CT_moved]=imwarp(CT,R_CT,T); 
[PET_moved,R_PET_moved]=imwarp(PET,R_PET,T); 
R_CT=R_CT_moved; 
R_PET=R_PET_moved; 
clear R_PET_moved R_CT_moved
%%
R_PET2=imref2d(size(PET),R_PET.XWorldLimits,R_PET.YWorldLimits);
R_CT2=imref2d(size(CT),R_CT.XWorldLimits,R_CT.YWorldLimits);
%% 
figure(nfig)
nfig=nfig+1; 
ax1 = axes;
h = imshow(b, R_PET2, 'Parent', ax1);  
colormap(ax1, jet);
colorbar(ax1);  
clim([0 max1])

%%
% [X, Y, Z] = meshgrid(1:sCT(1), 1:sCT(2), 1:sCT(3));
% % Coordenadas físicas para CT
% X_phys_CT = R_CT_moved.XWorldLimits(1) + (X - 1) * vCT(1);
% Y_phys_CT = R_CT_moved.YWorldLimits(1) + (Y - 1) * vCT(2);
% Z_phys_CT = R_CT_moved.ZWorldLimits(1) + (Z - 1) * vCT(3);
 
% [X1, Y1, Z1] = meshgrid(1:sPET(1), 1:sPET(2), 1:sPET(3));
% % Coordenadas físicas para PET
% X_phys_PET = R_PET_moved.XWorldLimits(1) + (X1 - 1) * vPET(1);
% Y_phys_PET = R_PET_moved.YWorldLimits(1) + (Y1 - 1) * vPET(2);
% Z_phys_PET = R_PET_moved.ZWorldLimits(1) + (Z1 - 1) * vPET(3);

%% interpolacion 

% Coordenadas originales
[x, y, z] = meshgrid (R_PET.XWorldLimits(1):vPET(1):(R_PET.XWorldLimits(2) - vPET(1)), ...
                   R_PET.YWorldLimits(1):vPET(2):(R_PET.YWorldLimits(2) - vPET(2)), ...
                   R_PET.ZWorldLimits(1):vPET(3):(R_PET.ZWorldLimits(2) - vPET(3)));

% Coordenadas de la nueva resolución (en el mundo real)
[xq, yq, zq] = meshgrid (R_PET.XWorldLimits(1):vCT(1):(R_PET.XWorldLimits(2) - vCT(1)), ...
                      R_PET.YWorldLimits(1):vCT(2):(R_PET.YWorldLimits(2) - vCT(2)), ...
                      R_PET.ZWorldLimits(1):vCT(3):(R_PET.ZWorldLimits(2) - vCT(3)));

interpolacion{1,1}='linear';
interpolacion{1,2}='nearest'; 
interpolacion{1,3}='cubic'; 
interpolacion{1,4}='makima';
interpolacion{1,5}='spline'; 
PET_interpolado = interp3(x, y, z, PET, xq, yq, zq,interpolacion{1,type_intp});

%%
R_PET_interpolado=imref3d(size(PET_interpolado),R_PET.XWorldLimits,R_PET.YWorldLimits,R_PET.ZWorldLimits);

b=PET_interpolado(:,:,nslice); 
R_PET2=imref2d(size(b),R_PET.XWorldLimits,R_PET.YWorldLimits); 

max2=max(PET_interpolado(:)); 
%%
%b=
figure(nfig)
nfig=nfig+1; 
ax1 = axes;
h = imshow(b, R_PET2, 'Parent', ax1);  
colormap(ax1, jet);
colorbar(ax1);  
clim([0 max2])

%% Expansion 

factor(1) = round(vPET(1)/vCT(1));     
factor(2) = round(vPET(2)/vCT(2));    
factor(3) = round(vPET(3)/vCT(3));    

PET_temp=zeros(sPET(1)*factor(1),sPET(2)*factor(2),sPET(3)); 
for i=1:sPET(3)
    PET_temp(:,:,i) = kron(PET(:,:,i), ones(factor(1), factor(2)));
end 

%escala=prod(factor); 
escala=1; 
% solo la voy a tener en cuenta cuando calcule la Actiivdad en un organo escala=1; 

% tengo que chequear esta parte 
PET_expandido = repmat(PET_temp, 1, 1, factor(3));
PET_expandido = PET_expandido./(escala); 

R_PET_expandido=imref3d(size(PET_expandido),R_PET.XWorldLimits,R_PET.YWorldLimits,R_PET.ZWorldLimits);


b=PET_expandido(:,:,nslice); 
R_PET21=imref2d(size(b),R_PET.XWorldLimits,R_PET.YWorldLimits); 
max3=max(PET_expandido(:)); 

figure(nfig)
nfig=nfig+1; 
clf
ax1 = axes;
h = imshow(b*escala, R_PET21, 'Parent', ax1);  
colormap(ax1, jet);
colorbar(ax1);  
clim([0 max3*escala])
%% 
max_=[max1,max2,max3*escala]; 

%% recorte expandido 

% ponsarlo en x y en z despues veo

posPETi(1)=R_CT.XWorldLimits(1); 
posPETi(2)=R_CT.YWorldLimits(1);
posPETi(3)=R_CT.ZWorldLimits(1); 

posPETf(1)=R_CT.XWorldLimits(2); 
posPETf(2)=R_CT.YWorldLimits(2);
posPETf(3)=R_CT.ZWorldLimits(2); 

ind_i(1)=(posPETi(1)-R_PET_expandido.XWorldLimits(1))/R_PET_expandido.PixelExtentInWorldX;
ind_i(1)=ind_i(1)+1; 
ind_i(2)=(posPETi(2)-R_PET_expandido.YWorldLimits(1))/R_PET_expandido.PixelExtentInWorldY;
ind_i(2)=ind_i(2)+1; 
ind_i(3)=(posPETi(3)-R_PET_expandido.ZWorldLimits(1))/R_PET_expandido.PixelExtentInWorldZ;
ind_i(3)=ind_i(3)+1; 

% analizar si hay que sumarle uno o no 
ind_i=round(ind_i); 

%% no usar posicion final sino ind_i+512 

ind_f(1)=(posPETf(1)-R_PET_expandido.XWorldLimits(1))/R_PET_expandido.PixelExtentInWorldX;
ind_f(1)=ind_f(1)+1; 
ind_f(2)=(posPETf(2)-R_PET_expandido.YWorldLimits(1))/R_PET_expandido.PixelExtentInWorldY;
ind_f(2)=ind_f(2)+1; 
ind_f(3)=(posPETf(3)-R_PET_expandido.ZWorldLimits(1))/R_PET_expandido.PixelExtentInWorldZ;
ind_f(3)=ind_f(3)+1; 

ind_f=round(ind_f); 

delta=ind_f-ind_i; 


b=PET_expandido(:,:,nslice); 

PET_expandido_recortado=PET_expandido(ind_i(1):ind_i(1)+sCT(1)-1,ind_i(2):ind_i(2)+sCT(2)-1,1:end); 

sPET_exp_rec=size(PET_expandido_recortado); 

PET_exp_completado=zeros(sCT); 
PET_exp_completado(:,:,1:sPET_exp_rec(3))=PET_expandido_recortado; 

%imshow(b,[])
%colormap(jet)
%clim([0 max3*escala])


%R_PET2_expandido=imref2d(size(b1),R_PET_expandido.PixelExtentInWorldX,R_PET_expandido.PixelExtentInWorldY); 

%PET_expandido_recortado=PET_expandido(ind(1):ind(1)+sCT(1),ind(2):ind(2)+sCT(2),ind(3):sPET(3)); 

% figure(nfig)
% nfig=nfig+1; 
% ax1 = axes;
% h = imshow(b1, R_PET2_expandido, 'Parent', ax1);  % Mostrar PET en su sistema de referencia
% %set(ax2, 'Color', 'none');  % Hacer transparente el fondo de ax2
% %set(h, 'AlphaData', 0.5);  % Ajustar transparencia de la imagen PET
% colormap(ax1, jet);
% colorbar(ax1);  % Agregar una barra de color solo para la imagen PET (opcional)
% %linkaxes([ax1, ax2],'xy');
% %axis(ax1, 'off');   % Mostrar ejes si quieres visualizar las coordenadas
% clim([0 max3*escala])

b1=PET_exp_completado(:,:,nslice); 

%% Actividad
%A=[]; 
A=PET_exp_completado./prod(factor); 
Actividad=sum(A(:));
Actividad_GBq_exp=Actividad/1e9; 
%% 
% figure(nfig)
% nfig=nfig+1; 
% ax1 = axes;
% imshow(a ./ max(a(:)),'Parent', ax1);  
% hold on 
% pos_ax1=ax1.Position; 
% ax2 = axes;
% set(ax2,'Position',pos_ax1)
% h = imshow(b1,'Parent', ax2);  
% set(ax2, 'Color', 'none');  
% set(h, 'AlphaData', 0.5); 
% colormap(ax2, jet);
% h=colorbar(ax2); 
% pos_bar=h.Position; 
% pos_bar(1)=pos_bar(1)+0.05; 
% set(h,'Position',pos_bar)
% axis(ax1,'off');   % Mostrar ejes si quieres visualizar las coordenadas
% clim([0 max3*escala])

max6=max(PET_exp_completado(:)); 
figure(nfig)
nfig=nfig+1; 
for i=1:sCT(3)
    clf
    a=double(CT(:,:,i));
    b=PET_exp_completado(:,:,i);
    ax1 = axes;
    pos_ax1=ax1.Position; 
    h = imshow(a./max(a(:)),'Parent', ax1);
    hold on 
    ax2 = axes;
    set(ax2,'Position',pos_ax1)
    h = imshow(b,'Parent', ax2);  
    set(ax2, 'Color', 'none');  
    set(h, 'AlphaData', 0.5); 
    colormap(ax2, jet);
    h=colorbar(ax2);  
    pos_bar=h.Position; 
    pos_bar(1)=pos_bar(1)+0.05; 
    set(h,'Position',pos_bar)
    clim([0 max6*escala])
    pause(0.1)
end 


%% recorte interpolado 
 
posPETi(1)=R_CT.XWorldLimits(1); 
posPETi(2)=R_CT.YWorldLimits(1);
posPETi(3)=R_CT.ZWorldLimits(1); 

posPETf(1)=R_CT.XWorldLimits(2); 
posPETf(2)=R_CT.YWorldLimits(2);
posPETf(3)=R_CT.ZWorldLimits(2); 

ind_i(1)=(posPETi(1)-R_PET_expandido.XWorldLimits(1))/R_PET_expandido.PixelExtentInWorldX;
ind_i(1)=ind_i(1)+1; 
ind_i(2)=(posPETi(2)-R_PET_expandido.YWorldLimits(1))/R_PET_expandido.PixelExtentInWorldY;
ind_i(2)=ind_i(2)+1; 
ind_i(3)=(posPETi(3)-R_PET_expandido.ZWorldLimits(1))/R_PET_expandido.PixelExtentInWorldZ;
ind_i(3)=ind_i(3)+1; 

% analizar si hay que sumarle uno o no 
ind_i=round(ind_i); 

ind_f(1)=(posPETf(1)-R_PET_interpolado.XWorldLimits(1))/R_PET_interpolado.PixelExtentInWorldX;
ind_f(1)=ind_f(1)+1; 
ind_f(2)=(posPETf(2)-R_PET_interpolado.YWorldLimits(1))/R_PET_interpolado.PixelExtentInWorldY;
ind_f(2)=ind_f(2)+1; 
ind_f(3)=(posPETf(3)-R_PET_interpolado.ZWorldLimits(1))/R_PET_interpolado.PixelExtentInWorldZ;
ind_f(3)=ind_f(3)+1; 

ind_f=round(ind_f); 

delta=ind_f-ind_i; 

b=PET_interpolado(:,:,nslice); 

b1=b(ind_i(1):ind_f(1),ind_i(2):ind_f(2)); 
PET_interpolado_cortado=PET_interpolado(ind_i(1):ind_i(1)+sCT(1)-1,ind_i(2):ind_i(2)+sCT(2)-1,1:end); 
sPET_intr_rec=size(PET_interpolado_cortado); 
PET_interpolado_completado=zeros(sCT); 
PET_interpolado_completado(:,:,1:sPET_intr_rec(3))=PET_interpolado_cortado; 
%% modificarlo aca para que quede de 512x512x127


b2=b1; 

R_PET2_interpolado=imref2d(size(b2),[0 ,R_PET_interpolado.PixelExtentInWorldX*size(b1,1)],[0 ,R_PET_interpolado.PixelExtentInWorldY*size(b1,2)]); 

%PET_expandido_recortado=PET_expandido(ind(1):ind(1)+sCT(1),ind(2):ind(2)+sCT(2),ind(3):sPET(3)); 

figure(nfig)
nfig=nfig+1; 
ax1 = axes;
h = imshow(b2, R_PET2_interpolado, 'Parent', ax1);  
colormap(ax1, jet);
colorbar(ax1); 
clim([0 max2])
%%
A=PET_interpolado_completado; 
Actividad=sum(A(:));
Actividad_GBq_int=Actividad/1e9; 

%% 
figure(nfig)
nfig=nfig+1; 
ax1 = axes;
imshow(a ./ max(a(:)), R_CT2, 'Parent', ax1);  
hold on 
ax2 = axes;
h = imshow(b2, R_PET2_interpolado, 'Parent', ax2);  
set(ax2, 'Color', 'none');  
set(h, 'AlphaData', 0.5);  
colormap(ax2, jet);
h=colorbar(ax2);  
pos_bar=h.Position; 
pos_bar(1)=pos_bar(1)+0.05; 
set(h,'Position',pos_bar)
axis(ax1, 'off');   
clim([0 max2])

%% 
figure(nfig)
nfig=nfig+1; 
ax1 = axes;
pos_ax1=ax1.Position; 
h = imshow(a./max(a(:)),'Parent', ax1);
hold on 
ax2 = axes;
set(ax2,'Position',pos_ax1)
h = imshow(b2,'Parent', ax2);  
set(ax2, 'Color', 'none');  
set(h, 'AlphaData', 0.5); 
colormap(ax2, jet);
h=colorbar(ax2);  
pos_bar=h.Position; 
pos_bar(1)=pos_bar(1)+0.05; 
set(h,'Position',pos_bar)
clim([0 max2])
%% 



max5=max(PET_interpolado_completado(:)); 
figure(nfig)
nfig=nfig+1; 
for i=1:sCT(3)
    clf
    a=double(CT(:,:,i));
    b=PET_interpolado_completado(:,:,i);
    ax1 = axes;
    pos_ax1=ax1.Position; 
    h = imshow(a./max(a(:)),'Parent', ax1);
    hold on 
    ax2 = axes;
    set(ax2,'Position',pos_ax1)
    h = imshow(b,'Parent', ax2);  
    set(ax2, 'Color', 'none');  
    set(h, 'AlphaData', 0.5); 
    colormap(ax2, jet);
    h=colorbar(ax2);  
    pos_bar=h.Position; 
    pos_bar(1)=pos_bar(1)+0.05; 
    set(h,'Position',pos_bar)
    clim([0 max5])
    pause(0.1)
end 


%% 
paciente.PET_intp.PET=PET_interpolado_completado; 
paciente.PET_intp.type_intp=interpolacion{1,type_intp}; 

paciente.PET_ext.PET=PET_exp_completado; 
paciente.PET_exp.factor=factor; 

save(file_paciente,'paciente')