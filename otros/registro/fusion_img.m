%clear all
close all 
%% agregar el path 
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
clear newpath currentdirectory
%%
dictionary = dicomdict('get');
clc
[PET,info_PET]=f_cargo_imagen(0);% 1 es tiff
PET=squeeze(PET);
PET=uint8(PET);

[CT,info_CT]=f_cargo_imagen(0);% 1 es tiff
CT=squeeze(CT);
CT=uint8(CT);
%CT=CT(:,:,end:-1:1); 

ImagePositionPatientCT=info_CT.ImagePositionPatient; %mm 
ImagePositionPatientPET=info_PET.ImagePositionPatient; %mm 
tvoxelPET=[4.07 4.07 2]; 
tvoxelCT=[0.78 0.78 0.8];

tx=ImagePositionPatientCT(1)-ImagePositionPatientPET(1);
tx=tx/tvoxelPET(1);
ty=ImagePositionPatientCT(2)-ImagePositionPatientPET(2);
ty=ty/tvoxelPET(1);
tz=ImagePositionPatientCT(3)-ImagePositionPatientPET(3);
tz=tz/tvoxelPET(3);

T=[1    0    0   0
   0    1    0   0
   0    0    1   0
   tx   ty   tz  1]; 

tranf=affine3d(T); 
PET=imwarp(PET,tranf);


% info_PET1=info_PET;
% info_PET1.ImagePositionPatient=info_CT.ImagePositionPatient; 
% s=size(PET);

%  figure(100)
%  for i=1:s(3);
%      subplot(2,1,1)
%      imshow(CT(:,:,i),[])
%      subplot(2,1,2)
%      imshow(PET1(:,:,i),[])
%      pause(0.25)
%  end

% sz=176/200; 
% sx=200/512;
% sy=sx;
% 
% T=[sx   0     0   0
%    0    1     0   0
%    0    0     1   0
%    0    0     0   1]; 
% 
% tranf=affine3d(T); 
% CT=imwarp(CT,tranf);
% 
% 
% T=[1    0      0   0
%    0    sy    0   0
%    0    0     1   0
%    0    0     0   1]; 
% 
% tranf=affine3d(T); 
% CT=imwarp(CT,tranf);
% 
% T=[1    0     0   0
%    0    1     0   0
%    0    0     sz   0
%    0    0     0   1]; 
% 
% tranf=affine3d(T); 
% CT=imwarp(CT,tranf);
% 
% 
% % sx=tvoxelPET(1)/tvoxelCT(1);
% % sy=tvoxelPET(2)/tvoxelCT(2);
% % sz=tvoxelPET(3)/tvoxelCT(3);
sz=376/172;

T=[1    0    0   0
   0    1    0   0
   0    0    sz   0
   0    0    0   1]; 
 
tranf=affine3d(T); 
PET=imwarp(PET,tranf);

% s2=size(PET2);
% figure(100)
% for i=1:s(3);
%      subplot(2,1,1)
%      imshow(CT(:,:,i),[])
%      subplot(2,1,2)
%      imshow(PET2(:,:,i),[])
%      pause(0.25)
% end
%  
% sx=512/200; 
% sy=sx; 
% T=[sx    0    0   0
%    0     1    0   0
%    0     0    1   0
%    0     0    0   1]; 
% 
% tranf=affine3d(T); 
% PET=imwarp(PET,tranf);
s=size(PET);

nfig=100;
figure(nfig)
set(gcf,'Render','OpenGL')
nfig=nfig+1;
max1=max(PET(:));
for nslice=1:s(3)
    imshow(CT(:,:,nslice),[]);
    h=title([' Fusion CT-SPECT # ',num2str(nslice)]);
    set(h,'FontWeight','bold')
    colormap(gray)
    freezeColors;
    hold on
    imshow(PET(:,:,nslice),[]);
    %colormap(jet(16))
    colormap(jet)
    caxis([0 max1])
    colorbar
    alpha 0.4
    pause(1)
end
 
%%  
% figure(101)
% for i=1:s(3)
%     imshowpair(CT(:,:,i),PET2(:,:,i));
%     pause(0.25)
% end 
% 
% 
% 
% for nslice=1:s(3)
%     file=['D:\Doctorado-seba\pet-',num2str(nslice),'.dcm'];
%     status=dicomwrite(PET1(:,:,nslice),file,info_PET1,'MultiframeSingleFile','true','CreateMode','Copy');
% end
%    
% modality='multimodal'; 
% %modality='monomodal';
% [optimizer,metric]= imregconfig(modality);
% optimizer.MaximumIterations=50;
% optimizer.InitialRadius=6.3e-7;
% 
% %new = imregister(CT,A,'affine',optimizer,metric,'DisplayOptimization',true,'PyramidLevels',4 );
% new1 = imregister(PET,A1,'affine',optimizer,metric,'DisplayOptimization',true,'PyramidLevels',4 );
% 
% 
%  figure(1)
%  for i=1:size(A,3);
%      subplot(2,1,1)
%      imshow(CT(:,:,i),[])
%      subplot(2,1,2)
%      imshow(new(:,:,i),[])
%      pause(0.01)
%  end
% 
%   figure(2)
%  for i=1:size(A,3);
%      subplot(2,1,1)
%      imshow(PET(:,:,i),[])
%      subplot(2,1,2)
%      imshow(new1(:,:,i),[])
%      pause(0.01)
%  end
% 
% % 
% % %  figure(1)
% %  for i=1:size(A,3);
% %      subplot(2,1,1)
% %      imshow(fusion(:,:,:,i),[])
% %      subplot(2,1,2)
% %      imshow(A(:,:,i),[])
% %      pause(0.01)
% %  end
% % 
% % 
% % %  figure(2)
% % %  BW=zeros(size(A));
% % %   for i=1:size(A,3)
% % %      [level,em] = graythresh(A(:,:,i));
% % %      BW(:,:,i) = im2bw(A(:,:,i),level);
% % %      subplot(2,1,1)
% % %      imshow(fusion(:,:,:,i),[])
% % %      subplot(2,1,2)
% % %      imshow(A(:,:,i),[])
% % %      pause(0.01)
% % %  end
% % 
% % figure(3)
% % fill_BW=zeros(size(A));
% % for i=1:size(A,3)
% %     fill_BW(:,:,i)=imfill(A(:,:,i),'holes');
% %     subplot(2,1,1)
% %     imshow(fusion(:,:,:,i),[])
% %     subplot(2,1,2)
% %     imshow(fill_BW(:,:,i),[])
% %     pause(0.01)
% % end
% % %
% % B=fill_BW;
% % clear fill_BW fusion A
% % 
% % B=uint8(B);
% % %tvoxel=[4,4,2];
% % %PET=uint8(PET); 
% % %PET=PET(:,:,end:-1:1); 
% % 
% % s_new=size(B);
% % [PET,ok.PET]=f_inter3D(PET,s_new);
% % CT=uint8(CT);
% % s_new=[512,512,376];
% % [CT,ok.CT]=f_inter3D(B,s_new);
% 
% %  figure(2)
% %  BW=zeros(size(PET));
% %   for i=1:size(PET,3)
% %      [level,em] = graythresh(PET(:,:,i));
% %      BW(:,:,i) = im2bw(PET(:,:,i),level);
% %      subplot(2,1,1)
% %      imshow(BW(:,:,i),[])
% %      subplot(2,1,2)
% %      imshow(B(:,:,i),[])
% %      pause(0.01)
% %   end
% % 
% %  figure(2)
% %  fill_BW=zeros(size(PET));
% %   for i=1:size(PET,3)
% %      fill_BW(:,:,i)=imfill(BW(:,:,i),'holes');
% %      subplot(2,1,1)
% %      imshow(fill_BW(:,:,i),[])
% %      subplot(2,1,2)
% %      imshow(B(:,:,i),[])
% %      pause(0.01)
% %   end
% 
% %C= smooth3(fill_BW);
%  
%  %figure(2)
%  %fill_BW=zeros(size(PET));
% %   for i=1:size(PET,3)
% %      subplot(2,1,1)
% %      imshow(C(:,:,i),[])
% %      subplot(2,1,2)
% %      imshow(B(:,:,i),[])
% %      pause(0.01)
% %   end
% % %  
% %  
% % % clear  fill_BW BW
% % %R_PET=imref3d(size(PET),tvoxel(1),tvoxel(2),tvoxel(3));
% % % 
% % % clc 
% % 
% % 
% % 
% % % s=[1 1 1];
% % % T=[s(1) 0   0  0
% % %     0  s(2) 0  0
% % %     0  0   s(3)  0
% % %     100  100  0     1];
% % % tform = affine3d(T);
% % 
% % % X1=A(:,:,250);
% % % X2=B(:,:,250);
% % % s_new=size(A);
% % % [PET1,ok.PET]=f_inter3D(PET,s_new);
% % 
% % 
% % % XFUSmaxmin = wfusimg(CT(:,:,250),PET1(:,:,250),'db2',1,'max','min');
% % % 
% % % XFUSmean = wfusimg(A(:,:,250),PET1(:,:,250),'db2',5,'mean','mean');
% % % imshow(XFUSmaxmin)
% % % figure(2)
% % % imshow(XFUSmean,[])
% % % transf=imregtform(A,B,'affine',optimizer,metric,'DisplayOptimization',true);
% % % [CT1]=imwarp(CT,tform);
% % % 
% % % for i=1:size(PET2,3)
% % %     imshowpair(PET2(:,:,i),B(:,:,i),'falsecolor');
% % %     pause(0.25)
% % % end 
% % % imfusion
