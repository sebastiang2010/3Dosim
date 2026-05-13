clc 
clear 
close all 

a=load('C:\MAT\3Dosim\paciente.mat'); 
paciente=a.paciente; 
clear a 

index=paciente.index; 

s=[51,51,51]; 
I=ones(s).*index.liver;

figure(600)
imshow(I(:,:,25),[])

PET=zeros(s); 
PET(25,25,25)=1.0; 

figure(601)
imshow(PET(:,:,25),[])

paciente.Phantom=I; 
paciente.PET_intp.PET=PET; 

