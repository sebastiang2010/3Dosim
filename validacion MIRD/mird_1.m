%validacion mird
clc 
% clear 
close all 
%%
t_voxel=[1 1 1]; %mm 
t_voxel=t_voxel./10; %cm 
vvoxel=prod(t_voxel); 

densidad=1.06; %liver  

%%
index.aire=1;
index.liver=90;
index.tejido_blando=30;
index.hueso=80; 
index.lung=50; 
index.tumor=100; %>100
%%
T_N=3; 
Actvidad_liver=60; %Bq
Actividad_tumor=Actvidad_liver.*T_N;
%%
% Radio de la esfera
r = 10;
% Tamaño de la matriz
dim = 100;
% Crear una matriz tridimensional de ceros
matrix = zeros(dim, dim, dim);

% Coordenadas del centro de la esfera
%center = dim / 2;
center=[60,30,80];

% Rellenar la matriz con la esfera
for x = 1:dim
    for y = 1:dim
        for z = 1:dim
            % Calcular la distancia al centro de la esfera
            distance = sqrt((x - center(1))^2 + (y - center(2))^2 + (z - center(3))^2);
            
            % Asignar el valor 1 si la distancia es menor o igual al radio de la esfera
            if distance <= r
                matrix(x, y, z) = 1;
            end
        end
    end
end


%% 
% figure(50)
% for i=1:size(Phantom,3)
%     imshow(matrix(:,:,i),[])
%     title(num2str(i))
%     pause(1)
% end 
% ok 
%% 
IND_tumor=matrix==1;
IND_liver=matrix==0;

%%
volumen_tumor=sum(IND_tumor(:))*vvoxel; 
volumen_liver=sum(IND_liver(:))*vvoxel; 
m_liver=volumen_liver*densidad/1000; %kg  
m_tumor=volumen_tumor*densidad/1000; %kg
%%
PET=matrix; 
PET(IND_tumor)=Actividad_tumor; 
PET(IND_liver)=Actvidad_liver; 
%%
%imshow(matrix(:,:,72),[])
%%
Phantom=matrix; 
Phantom(IND_tumor)=index.tumor; 
Phantom(IND_liver)=index.liver; 
%%
k=48.98; % constante J-s 
SF=0; 
FU_normal=(1-SF)*(volumen_liver/(T_N*volumen_tumor+volumen_liver));
FU_tumor=(1-SF)*(T_N*volumen_tumor/(T_N*volumen_tumor+volumen_liver));

A=sum(PET(:));
A_GBq=A/1e9; 

%Actividad_GBq=D_tumor*m_tumor/(k*FU_tumor);
D_liver_Gy=A_GBq*k*FU_normal/m_liver; 
D_tumor_Gy=A_GBq*k*FU_tumor/m_tumor; 
%% 


