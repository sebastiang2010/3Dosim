A=rand(66,99,10);

[Xi,Yi,Zi]=meshgrid(1:99/386:399/4,1:66/250:267/4,1:1:3); %revisarq que de bien 








% %interp3
% clear all
% close all
% 
% % [x,y,z,v] = flow(10); 
% % [xi,yi,zi] = meshgrid(.1:.25:10, -3:.25:3, -3:.25:3);
% % vi = interp3(x,y,z,v,xi,yi,zi); % vi is 25-by-40-by-25
% % slice(xi,yi,zi,vi,[6 9.5],2,[-2 .2]), shading flat
% 
% 
% A=rand(128,128,3);
% oldrows=size(A,1);
% oldcolum=size(A,2);
% nslice=size(A,3);
% newrows=512;
% newcols=512;
% 
% figure(1)
% imshow(A(:,:,2),[]);
% colormap(jet)
% 
% % quiero una de 256,256,3
% %[X,Y,Z]=meshgrid(1:0.5:256,1:0.5:256,1:1:3);
% [Xi,Yi,Zi]=meshgrid(1:128/516:128,1:128/516:128,1:1:3); %revisarq que de bien 






% 
% %VI = interp3(X,Y,Z,V,XI,YI,ZI)
% B=interp3(A,Xi,Yi,Zi,'cubic');

% figure(2)
% imshow(B(:,:,2),[]);
% colormap(jet)
% 
% %B 512*512 a A1 128*128
% 
% %[X,Y,Z]=meshgrid(1:0.5:256,1:0.5:256,1:1:3);
% [Xi,Yi,Zi]=meshgrid(1:512/128:512,1:512/128:512,1:1:3); %revisarq que de bien 
% 
% %reducir la imagen
% %B 512x512
% %VI = interp3(X,Y,Z,V,XI,YI,ZI)
% A1=interp3(B,Xi,Yi,Zi,'cubic');
% 
% figure(3)
% imshow(A1(:,:,2),[]);
% colormap(jet)
% 
% A2=(A-A1)*100./A1;
% 
% imshow(A2(:,:,3),[])
% colorbar(jet)