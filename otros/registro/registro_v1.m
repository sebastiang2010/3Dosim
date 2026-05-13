%% registro 
%clear all 
close all 
clc
%% 
%
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
%
directorio=f_creo_directorio;
% %%
% index_aire=1;
% index_skin=2;
% index_blando=3;
% index_hueso=4;
% index_fuente=0;

%% cargo tiff
 tiff=0; %1 tiff 0 dicom
% [PET,info_PET]=f_cargo_imagen(tiff);
% PET=squeeze(PET);
% PET=uint8(PET); % para ver el aire de los pulmones
% 
% [CT,info_CT]=f_cargo_imagen(tiff);
% CT=squeeze(CT);
% CT=uint8(CT); % para ver el aire de los pulmones
% % % 
% 
%%PET 
ps=info_PET.PixelSpacing;
% ImagePositionPET=info_PET.ImagePositionPatient;
ipp=info_PET.ImagePositionPatient;
SThickness=info_PET.SliceThickness;
iop=info_PET.ImageOrientationPatient;
%PixelSpacingPET=info_PET.PixelSpacing;  




%tform = affine3d([Sx 0 0 0; 0 Sy 0 0; 0 0 Sz 0; 0 0 0 1]);
%tform = affine3d([1 0 0 0; 0 1 0 0; 0 0 1 0; 0 0 0 1]);
%TF = isTranslation(tform);  %version 2015
%clear CT 

%outputImage = imwarp(PET(:,:,:),tform);
%figure, imshowpair(PET(:,:,100),outputImage(:,:,100));




%Matriz de traslacion
Tipp=[1 0 0 ipp(1);
      0 1 0 ipp(2);
     0 0 1 ipp(3);
     0 0 0 1];
r=iop(1:3);
c=iop(4:6);
s=cross(r',c');

R=[r(1) c(1) s(1) 0;
    r(2) c(2) s(2) 0;
    r(3) c(3) s(3) 0;
    0    0    0    1];

S=[ps(2) 0     0          0;
    0     ps(1) 0          0;
    0     0     SThickness 0;
    0     0     0          1];

To=[1 0 0 0;0 1 0 0;0 0 1 0;0 0 0 1];

M=Tipp*R*S*To;

MPET=M;
RPET=R; 

%%CT
ps=info_CT.PixelSpacing;
% ImagePositionPET=info_PET.ImagePositionPatient;
ipp=info_CT.ImagePositionPatient;
SThickness=info_CT.SliceThickness;
iop=info_CT.ImageOrientationPatient;
%PixelSpacingPET=info_PET.PixelSpacing;  

%tform = affine3d([Sx 0 0 0; 0 Sy 0 0; 0 0 Sz 0; 0 0 0 1]);
%tform = affine3d([1 0 0 0; 0 1 0 0; 0 0 1 0; 0 0 0 1]);
%TF = isTranslation(tform);  %version 2015
%clear CT 

%outputImage = imwarp(PET(:,:,:),tform);
%figure, imshowpair(PET(:,:,100),outputImage(:,:,100));

ps=info_CT.PixelSpacing;
% ImagePositionPET=info_PET.ImagePositionPatient;
ipp=info_CT.ImagePositionPatient;
SThickness=info_CT.SliceThickness;
iop=info_CT.ImageOrientationPatient;


%Matriz de traslacion
Tipp=[1 0 0 ipp(1);
      0 1 0 ipp(2);
      0 0 1 ipp(3);
      0 0 0 1];
r=iop(1:3);
c=iop(4:6);
s=cross(r',c');

R=[r(1) c(1) s(1) 0;
   r(2) c(2) s(2) 0;
   r(3) c(3) s(3) 0;
   0    0    0    1];

S=[ps(2) 0     0           0;
    0     ps(1) 0          0;
    0     0     SThickness 0;
    0     0     0          1];

To=[1 0 0 0;0 1 0 0;0 0 1 0;0 0 0 1];

M=Tipp*R*S*To;

MCT=M; 
RCT=R; 

M1=inv(MPET)*(To);
M1=M1'; 

T1=[0.5  0    0   0
    0    0.5  0   0
    0    0    0.5 0
    0    0    0   1];
M2=inv(MCT)*T1;
M2=M2'; 

A=M2*MCT;
tform = affine3d(M1); 
tform2 = affine3d(M2); 

% agregar imref3d

CT1=imwarp(CT(:,:,:),tform2); 
PET1= imwarp(PET(:,:,:),tform);
 





