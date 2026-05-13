close all 
%clear all 
clc
%% 
% %
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
%
directorio=f_creo_directorio;
%%  
clc 
nfig=1; 
%% cargo tiff
tiff=1; %1 tiff 0 dicom

% [CT,info_CT]=f_cargo_imagen(tiff);
% CT=squeeze(CT);
% CT=uint8(CT); 

CT=double(CT);
[thresh,metric] = multithresh(CT(:,:,20),15);

seg_CT = imquantize(CT(:,:,20),thresh);

figure(1)
imshow(seg_CT,[])


A=seg_CT==4;
figure()
imshow(A,[])

B=uint8(A).*uint8(CT(:,:,20));

figure(7)
imshow(log(double(B)),[])

B=double(B);
[thresh,metric] = multithresh(log(B),3);

seg_B = imquantize(log(B),thresh);

figure(8)
imshow(seg_B,[])

A=seg_B==2;
figure(8)
imshow(A,[])

C=double(A).*CT(:,:,20);


figure(8)
imshow(C,[])

%  repito=1;
%     for i=1:repito
%         h=fspecial('gaussian',4,7);
%         C= imfilter(C,h);
%         
%         
%         
%     end
    

 

[thresh,metric] = multithresh(C,3);

seg_C = imquantize(C,thresh);

A=seg_B==2;
figure(8)
imshow(A,[])




% clusters=4;
% [mu,maks]=f_kmeans(seg_B,clusters);


