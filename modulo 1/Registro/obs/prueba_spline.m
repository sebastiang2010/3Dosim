%% prueba interpolacion 
interp='cubic';
clc 
clear 
close all 


I=zeros(3,3,3);
I(2,2,2)=1; 
sI=[10,10,10]; %mm 

suma_inicial=sum(I(:)); 
sF=[1,1,1]; % 1 mm 

tvoxel=sI./sF;
tvoxel=round(tvoxel,2);
tvoxel(2)=tvoxel(1); 

S=[tvoxel(1) 0   0 0 
    0  tvoxel(2) 0 0
    0  0        tvoxel(3) 0
    0  0               0 1]; 

tranf=affine3d(S);
F=imwarp(I,tranf,'cubic');

a=sum(F(:));

A=F./a; 

figure(1)
imshow(F(:,:,15),[]); 
colormap(jet)
colorbar

figure(2)
imshow(A(:,:,15),[]); 
colormap(jet)
colorbar

b=sum(A(:)); 
