% Leer los archivos DICOM
%info_CT = dicominfo('CT_image.dcm'); % Información de la imagen CT
%info_PET = dicominfo('PET_image.dcm'); % Información de la imagen PET
%PET_slice=PET; 

clc 
close all 

% Suponiendo que ya tienes los volúmenes PET y CT cargados como PET y CT
% y las matrices de transformación info_PET y info_CT que contienen
% ImagePositionPatient y ImageOrientationPatient.

% Definir los límites del espacio físico de las imágenes
% R_PET = info_PET.PixelSpacing; % PixelSpacing de PET
% R_CT = info_CT.PixelSpacing;   % PixelSpacing de CT
% Z_PET = info_PET.SliceThickness; % SliceThickness de PET
% Z_CT = info_CT.SliceThickness;  % SliceThickness de CT
vCT=[0.81,0.81,1.5]; 

sCT=size(CT);
sPET=size(PET);

R_PET=imref3d(size(PET),[ippPET(1) ippPET(1)+vPET(1)*size(PET,1)],[ippPET(2) ippPET(2)+vPET(2)*size(PET,2)],[ippPET(3) ippPET(3)+vPET(3)*size(PET,3)]);
R_CT=imref3d(size(CT),[ippCT(1) ippCT(1)+vCT(1)*size(CT,1)],[ippCT(2) ippCT(2)+vCT(2)*size(CT,2)],[ippCT(3) ippCT(3)+vCT(3)*size(CT,3)]);

delta=[ippCT(1)-ippPET(1),ippCT(2)-ippPET(2),ippCT(3)-ippPET(3)]; 


tranf = affine3d([1 0 0 0; 0 1 0 0; 0 0 1 0; delta(1) delta(2) delta(3) 1]);

R_PET_moved=R_PET; 
R_CT_moved=R_CT; 

