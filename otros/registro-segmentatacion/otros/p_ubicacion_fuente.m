clear all
clc

I=zeros(512,512);

pos_fuente=[132,166];
%y=132;
%x=166;

% I(x,y)=255;
% I(x:x+5,y:y+5)=255;

% figure(1)
% imshow(I(:,:),[]);

corte=[152 401 61 446];

%hay que cambiar el orden 
% I(xmin:xmax,:)=255;
% I(:,ymin:ymax)=150;
% 
% I(x,y)=255;
% I(x:x+5,y:y+5)=255;
% 
% figure(2)
% imshow(I(:,:),[]);
% 
% A=I(xmin:xmax,ymin:ymax);
% 
% figure(3);
% imshow(A,[])
% 
% size(A)

% x1=y-xmin+(512-ymax)
% y1=x-ymin+(512-xmax)

pos(1)=pos_fuente(1)-corte(1)+512-corte(4);
pos(2)=pos_fuente(2)-corte(2)+512-corte(3);