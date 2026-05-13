clc 
clear 
close all

%%
a=load('C:\MAT\3Dosim\Check\paciente.mat');  
paciente=a.paciente; 
clear a 
% 
nfig=1; 
tipointp='nearest';
%tipointp='linear'; 

index=paciente.index; 
s=[81 101 21]; 
s=s*3; 

a=150;
b=230;
c=10;
d=15;
e=11; 

a1=10;
b1=15;
c1=150;
d1=230; 
e1=40; 

I=ones(s).*index.aire;
I(a:b,c:d,e)=index.liver;
I(a1:b1,c1:d1,e1)=index.liver;

figure(nfig)
nfig=nfig+1;
imshow(I(:,:,e),[])
figure(nfig)
nfig=nfig+1;
imshow(I(:,:,e1),[])


R_CT=imref3d(size(I)); 

PET=zeros(s); 

%PET(a:b,c:d,e)=1;

%figure(nfig)
%nfig=nfig+1;
%imshow(PET(:,:,11),[])

delta=0.5;
delta1=1-delta; 
for i=a:b
    delta1=delta1+delta; 
    PET(i,c:d,e)=delta1;
end     

delta=0.5;
delta1=1-delta; 
for i=c1:d1
    delta1=delta1+delta; 
    PET(a1:b1,i,e1-1:e1+1)=delta1;
end     


PET=PET.*1000;

figure(nfig)
nfig=nfig+1;
imshow(PET(:,:,e),[])
colormap(jet)
figure(nfig)
nfig=nfig+1;
imshow(PET(:,:,e1),[])
colormap(jet)

R_PET=imref3d(size(PET));

%% 
% Escala deseada de voxel (en mm)
voxelX_new = 4;
voxelY_new = 4;
voxelZ_new = 2;

% Escala actual de voxel
voxelX_old = R_PET.PixelExtentInWorldX;
voxelY_old = R_PET.PixelExtentInWorldY;
voxelZ_old = R_PET.PixelExtentInWorldZ;

% Calcular factores de escala (actual / nuevo)
sx = voxelX_old / voxelX_new;
sy = voxelY_old / voxelY_new;
sz = voxelZ_old / voxelZ_new;

% Construir matriz de transformación de escala
T = eye(4);
T(1,1) = sx;
T(2,2) = sy;
T(3,3) = sz;

% Crear objeto de transformación
tform = affine3d(T);

% Aplicar transformación (esto reescala la imagen)
[PET_1,R_PET11] = imwarp(PET, R_PET, tform, ...
                            'Interp',tipointp);

newSize = size(PET_1);

%% 3. Calcular nuevos límites espaciales
xWorldLimits = [0, voxelX_new * newSize(2)];
yWorldLimits = [0, voxelY_new * newSize(1)];
zWorldLimits = [0, voxelZ_new * newSize(3)];

% 4. Crear nueva referencia espacial
R_PET1 = imref3d(newSize, xWorldLimits, yWorldLimits, zWorldLimits);

a=PET_1(:,:,1);
R2 = imref2d(size(a), R_PET1.XWorldLimits, R_PET1.YWorldLimits);

figure(nfig)
nfig=nfig+1;
for i=1:size(PET_1,3)
    a=PET_1(:,:,i);
    imshow(a, R2, [])
    colormap(jet)
    title(num2str(i))
    pause(0.5)
end 

ind=find(PET_1>0); 
[x,y,z]=ind2sub(size(PET_1),ind); 
%% 
% Copiar la referencia original
R_2 = R_PET;

% Cantidades de traslación en mm
dx = 10;   % traslación en X
dy = -5;   % traslación en Y
dz = 30;   % traslación en Z

% Aplicar traslación modificando directamente los límites físicos
R_2.XWorldLimits = R_2.XWorldLimits + dx;
R_2.YWorldLimits = R_2.YWorldLimits + dy;
R_2.ZWorldLimits = R_2.ZWorldLimits + dz;


a=PET_1(:,:,1);
R2 = imref2d(size(a), R_2.XWorldLimits, R_2.YWorldLimits);

figure(nfig)
nfig=nfig+1;
for i=1:size(PET_1,3)
    a=PET_1(:,:,i);
    imshow(a, R2, [])
    colormap(jet)
    title(num2str(i))
    pause(0.5)
end 

% figure(nfig)
% nfig=nfig+1;
% %i=1:size(PET_1,3)
% a=PET_1(:,:,);
% imshow(a, R2, [])
% colormap(jet)
% title(num2str(6))
% pause(0.5)
% %end 

%% 
paciente.PET_check.PET=PET_1;
paciente.PET_check.R=R_PET1; 
paciente.CT_check.CT=I; 
paciente.CT_check.R=R_CT; 
