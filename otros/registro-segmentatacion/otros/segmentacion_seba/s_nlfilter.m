close all

tiff=1; %1 tiff 0 dicom
[I,image_info]=f_cargo_imagen(tiff);
I=squeeze(I);
%I=uint8(I); % para ver el aire de los pulmones
I=im2double(I);

I1=I(:,:,5);

L = del2(im2double(I1)); % laplaciano discreto 
imshow(L,[])
imhist(L)

h=fspecial('gaussian',2,5);
L1= imfilter(L,h);

[level,em] = graythresh(L1);
BW = im2bw(L1,level);
imshow(BW)


A=I1.*BW;
imshow(A,[]);

% A=bwareaopen(A,5);
% imshow(A,[]);      
[L, num] = bwlabel(A, 8);

for i=1:num(end)
    imshow(L==i,[]);
end


se = strel('disk',1);
bw_hueso = imclose(bw_hueso,se);


% %A = imread('cameraman.tif'); 
% I1 = im2double(I1);
% h=fspecial('gaussian',2,2);
% %I1
% fun = @(x) median(x(:)); 
I2 = nlfilter(A,[3 3],'std2')*6; 
I2= imfilter(I2,h);
imshow(I1,[]), figure, imshow(I2,[])
figure(100)
% 
% figure(101)
% imhist(I2)