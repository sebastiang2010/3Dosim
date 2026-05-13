clc 
clear 
close all 


Dosis=rand(100,100,50).*0.03; 

max1=max(Dosis(:)); 

x=40; 
y=30;   

slice=20; 

figure(100)
imshow(Dosis(:,:,slice),[])
clim([0,max1])
colormap(jet)

b=Dosis(y,x,slice); 

IND=zeros(100,100,50); 
IND(10:60,20:60,slice)=1; 

figure(101)
imshow(IND(:,:,slice),[])

A=Dosis.*IND.*0.9;
a=A(y,x,slice); 

max2=max(A(:));
figure(101)
imshow(A(:,:,slice),[])
clim([0,max2])
colormap(jet)
