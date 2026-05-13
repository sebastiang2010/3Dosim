clc 
clear 
close all
%%
a=load('C:\MAT\3Dosim\paciente.mat'); 
%% 
paciente=a.paciente; 
clear a 
% 
index=paciente.index; 
s=[81 101 21]; 

I=ones(s).*index.aire;
I(50:70,10:15,11)=index.liver;

figure(200)
imshow(I(:,:,11),[])


PET=zeros(s); 
PET(50:70,10:15,11)=1;

figure(100)
imshow(PET(:,:,11),[])

delta=0.5;
a=1-delta; 
for i=50:70
    a=a+delta; 
    PET(i,10:15,11)=a;
end     

figure(101)
imshow(PET(:,:,11),[])
colormap(jet)