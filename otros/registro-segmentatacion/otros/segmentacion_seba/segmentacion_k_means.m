% repeat the clustering 3 times to avoid local minima

close all 
clc
%% 
%
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
%
directorio=f_creo_directorio;
% 
%% cargo tiff
% tiff=0; %1 tiff 0 dicom
% [PET,info_PET]=f_cargo_imagen(tiff);
% PET=squeeze(PET);
% PET=uint8(PET); % para ver el aire de los pulmones

[CT,info_CT]=f_cargo_imagen(tiff);
CT=squeeze(CT);
CT=uint8(CT); % para ver el aire de los pulmones
% % 



[cluster_idx, cluster_center] = kmeans(ab,nColors,'distance','sqEuclidean', ...
                                      'Replicates',3);