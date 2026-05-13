%% segmentacion usando nii 
%% 27/02/18

%% generar un paciente_register
%clear all
close all
clc
%% agregar el path 
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
clear newpath currentdirectory
%%
directorio=f_creo_directorio;
%% 
interp='cubic';
angle=90; 
%%
index.aire=1;
index.skin=2;
index.blando=30;
index.liver=50;
index.bone=5;
index.lung=6; 
index.tumor=100;
%
fig=1; 
%% agregar funcion creo directorio 
%dictionary = dicomdict('get');
tipo=0; %DICOM 
% clc
%[PET,info_PET]=f_cargo_imagen(tipo);% 1 es tiff
%PET=squeeze(PET);
%chequear factor de calibracion 
% chequear units (BQML)

%% chequear la modalidad 
[CT,info_CT]=f_cargo_imagen(tipo);% 1 es tiff
%CT=squeeze(CT);
%CT=int16(CT);

%vCT=[info_CT.PixelSpacing;info_CT.SingleCollimationWidth/info_CT.SpiralPitchFactor]; %mm
%% pasaje a HU %%hacer funcion 
%CT=f_HU(CT,info_CT); 
%PET=f_HU(PET,info_PET); %para pasar a Bq/ml  

figure(2)
imtool(CT(:,:,255),[])
 
%% Analize MITK 
liver1=f_cargar_nii; %estructura 

for i=1:size(liver1.img,3)
    liver(:,:,i)=imrotate(liver1.img(:,:,i),angle);
end 
clear liver1
a=max(liver1.img(:));
IND=a==liver1.img;
liver1.img(IND)=index.liver;
liver=zeros(size(liver1.img)); 

%% 
a=min(CT(:));
CT(IND)=a; 
%
fig=fig+1; 
figure(fig)
imtool(CT(:,:,225),[])
%% TUMOR 
%tumor=f_cargar_nii; %estructura 
a=max(tumor.img(:));
IND=a==tumor.img;
tumor.img(IND)=index.tumor; 
%% 
fig=fig+1; 
figure(fig)
imtool(tumor.img(:,:,315),[])
%%
CT(IND)=255; 
%%
fig=fig+1; 
figure(fig)
imshow(A(:,:,315),[])


