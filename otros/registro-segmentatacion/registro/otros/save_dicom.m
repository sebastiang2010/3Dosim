%clear all
clc
close all 
%% agregar el path 
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
clear newpath currentdirectory
%%
%% agregar funcion creo directorio 
%dictionary = dicomdict('get');
tipo=0; 
clc
[PET,info_PET]=f_cargo_imagen(tipo);% 1 es tiff
PET=squeeze(PET);
%PET=uint16(PET);
  
%ippCT=info_CT.ImagePositionPatient; %mm 
ippPET=info_PET.ImagePositionPatient; %mm 
ippPET=[-100;-100;-400]; 

info_PET.ImagePositionPatient=ippPET; 

%vPET=[info_PET.PixelSpacing;info_PET.SliceThickness]; %mm
%vCT=[info_CT.PixelSpacing;info_CT.SliceThickness]; %mm
UID = dicomuid;  
%a='CT Image Storage';

directorio='D:\MAT\PET\'; 
for i=1:size(PET,3)
    file=num2str(i); 
    file2=[directorio,file,'.dcm'];
    %file_unico='D:\MAT\PET\PET_dicom.dcm';
    status=dicomwrite(PET(:,:,i),file2,info_PET,'CreateMode','copy','MultiframeSingleFile','false');
    %status=dicomwrite(PET(:,:,i),file_unico,info_PET,'CreateMode','copy','MultiframeSingleFile','true');
    clc
    disp(' ')
    disp(num2str(i))
    pause(0.02)
end 