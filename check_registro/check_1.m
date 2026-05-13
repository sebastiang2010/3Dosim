clc 
clear 
close all
%%
a=load('C:\MAT\3Dosim\Check\paciente.mat'); 
%% 
paciente=a.paciente; 
clear a 
% 
index=paciente.index; 
s=[81 101 21]; 

I=ones(s).*index.aire;
I(50:70,10:15,11)=index.liver;

figure(200)
imshow(I(:,:,11),[])


PET=zeros(s); 
PET(50:70,10:15,11)=1;

figure(100)
imshow(PET(:,:,11),[])

delta=0.5;
a=1-delta; 
for i=50:70
    a=a+delta; 
    PET(i,10:15,11)=a;
end     

PET=PET.*1000;

figure(101)
imshow(PET(:,:,11),[])
colormap(jet)

%% 
s_I=size(I);
%R_1=imref3d; 
R_1=imref3d(s_I);
v_I = [1.0, 1.0, 1.0];        % mm/voxel en X, Y, Z

% Factor de escalado
scaleFactor = 1;

% Matriz de transformación afín (4x4) para escalado
T = eye(4);
T(1,1) =1/scaleFactor;
T(2,2) = 1/scaleFactor;
T(3,3) = 1/1; % ver que pasa con 4 

% Crear el objeto de transformación afín
tform = affine3d(T);

% Aplicar la transformación
outputRef = imref3d(s_I, v_I(1), v_I(2), v_I(3));
%[PET,R_2] = imwarp(PET, outputRef, tform);
tipointp='nearest'; 
[PET_2, R_2] = imwarp(PET, outputRef, tform, 'Interpolation', tipointp);

a=PET_2;
R2 = imref2d(size(a), R_2.XWorldLimits, R_2.YWorldLimits);
figure(356)
for i=1:size(PET_2,3)
    a=PET_2(:,:,i);
    imshow(a, R2, [])
    colormap(jet)
    pause(0.5)
end

%% Revisar que corre la imagen  
% 
%% 

% Centro del volumen en coordenadas físicas
center = [(R_2.XWorldLimits(1) + R_2.XWorldLimits(2)) / 2, ...
          (R_2.YWorldLimits(1) + R_2.YWorldLimits(2)) / 2, ...
          (R_2.ZWorldLimits(1) + R_2.ZWorldLimits(2)) / 2];

%% 🔁 Generar rotación aleatoria
% Ángulo aleatorio en grados
%angle_deg = rand()*360;
angle_deg=60; 
angle_rad = deg2rad(angle_deg);

% Eje aleatorio normalizado
%axis = rand(1,3);
%axis = axis / norm(axis);
axis = [0 0 1]; % es una rotacion respecto del eje z 



% Crear matriz de rotación 3D usando axis-angle
R = axang2rotm([axis angle_rad]);  % Requiere Robotics System Toolbox

% Armar matriz de rotación homogénea (4x4)
T_rot = eye(4);
T_rot(1:3,1:3) = R;

%% 🧭 Generar traslación aleatoria (en mm)
t = (rand(1,3)-0.5)*40;  % traslación aleatoria entre -20 y 20 mm
t=[10 10 1];

T_trans = eye(4);
T_trans(4,1:3) = t;

%% 🧠 Transformaciones respecto al centro
T_to_origin = eye(4);
T_to_origin(4,1:3) = -center;

T_back = eye(4);
T_back(4,1:3) = center;

%% 🔀 Componer transformación total
T_total = T_to_origin * T_rot * T_back;% * T_trans;

tform = affine3d(T_total);

%% ✨ Aplicar transformación
[PET_3, R_3] = imwarp(PET_2,R_2, tform,'Interp', 'linear');
%[PET_3, R_3] = imwarp(PET_2, R_2, tform, 'Interp', tipointp, ...
%   'OutputView', R_2);  % ❗️ mantener dimensiones originales

a=PET_3(:,:,1);
R2 = imref2d(size(a), R_3.XWorldLimits, R_3.YWorldLimits);

figure(103)
for i=1:size(PET_3,3)
    a=PET_3(:,:,i);
    imshow(a, R2, [])
    colormap(jet)
    title(num2str(i))
    pause(0.5)
end 

% %% 📊 Mostrar resultados
% disp('Ángulo de rotación [°]:');
% disp(angle_deg);
% disp('Eje de rotación:');
% disp(axis);
% disp('Vector de traslación [mm]:');
% disp(t);
% disp('Nuevos límites del mundo real:');
% disp(refTransformed.XWorldLimits);
% disp(refTransformed.YWorldLimits);
% disp(refTransformed.ZWorldLimits);
% 

T = eye(4);
T(1,1) =1/4;
T(2,2) = 1/4;
T(3,3) = 1/2; % ver que pasa con 4 

% Crear el objeto de transformación afín
tform = affine3d(T);

% Aplicar la transformación
%outputRef = imref3d(size(PET_3, v_I(1), v_I(2), v_I(3)));
%[PET,R_2] = imwarp(PET, outputRef, tform);
tipointp='nearest'; 
[PET_4, R_4] = imwarp(PET_3, R_3, tform, 'Interpolation', tipointp);


a=PET_4(:,:,1);
R2 = imref2d(size(a), R_3.XWorldLimits, R_3.YWorldLimits);

figure(104)
for i=1:size(PET_4,3)
    a=PET_4(:,:,i);
    imshow(a, R2, [])
    colormap(jet)
    title(num2str(i))
    pause(0.4)
end 
%%
% Nuevos tamaños de voxel
voxelX = 4;
voxelY = 4;
voxelZ = 8;

% Tamaño de imagen
imageSize =size(PET_4);  % [Y X Z]

% Calcular nuevos límites físicos
xWorld = [0, voxelX * imageSize(2)];
yWorld = [0, voxelY * imageSize(1)];
zWorld = [0, voxelZ * imageSize(3)];

% Crear nuevo objeto imref3d
R_41 = imref3d(imageSize, xWorld, yWorld, zWorld);

paciente.PET_4.PET=PET_4; 
paciente.PET_4.R=R_4; 