function [recorte] = f_recorte(I)
%UNTITLED Summary of this function goes here
%   Detailed explanation goes here

recorte=[];
disp(' ')
parar=input(' Quisiera recortar la imagen // Si~=0 // No=0 : ');

while parar~=0
    figure(100)
    imshow(I(:,:,round(size(I,3)/2)),[])
    h=imrect;
    recorte=wait(h);
    %[xmin ymin width height]
    recorte=round(recorte);
    I1=I(recorte(2):recorte(2)+recorte(4),recorte(1):recorte(1)+recorte(3),:);
    
    figure(100)
    for nslice=1:size(I,3)
        imshow(I1(:,:,nslice))
        colormap(jet)
        pause(0.1)
    end
    
    clc 
    disp('  ')
    parar=input('  La imagen se corto correctemente // Si=0 // No~=0 : ');
end
end


