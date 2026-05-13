%function [I,dicominfo,voxel]=f_dicom2tiff(tiff)


clc
tiff=0; %dicom 
[I,dicominfo]=f_cargo_imagen(tiff);

I=squeeze(I);

%% pendiente y ordenada al origen 
% m=dicominfo.RescaleSlope;
% b=dicominfo.RescaleIntercept;
% 
% I=I.*m+b; % esta en unidades H
% 
a=dicominfo.PixelSpacing;
b=dicominfo.SliceThickness;
%
voxel=[a(1),a(2),b];
%% 
%grabo como tiff de 256 colores
I=uint16(I);
%I=unit8(I);

clc
file='D:\MAT\Emergencias\dicom2tiff.tif';
delete(file);
for i=1:size(I,3)
    imwrite(I(:,:,i),file,'tiff','WriteMode','append')
end
disp('  ')
disp('Se genero un tiff (I_original.tiff)')
