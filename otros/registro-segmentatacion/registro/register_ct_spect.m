
%% generar un paciente_register
%clear all
close all
clc
%% agregar el path 
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
clear newpath currentdirectory
%%
directorio=f_creo_directorio;
%% 
interp='cubic';
%% agregar funcion creo directorio 
%dictionary = dicomdict('get');
tipo=0; 
clc
[PET,info_PET]=f_cargo_imagen(tipo);% 1 es tiff
 PET=squeeze(PET);
%chequear factor de calibracion 
% chequear units (BQML)

%% chequear la modalidad 
[CT,info_CT]=f_cargo_imagen(tipo);% 1 es tiff
CT=squeeze(CT);

%% pasaje a HU %%hacer funcion 
%CT=f_HU(CT,info_CT); 
%PET=f_HU(PET,info_PET); %para pasar a Bq/ml  
 
CT=uint8(CT); 
PET=uint8(PET);

helperVolumeRegistration(CT,PET);
%  %%%%CT=CT(:,:,end:-1:1); 
%  for i=1:size(PET,3)
%    PET1(:,:,i) = imadjust(PET(:,:,i));
%  end 
%   
% 
% max1=max(PET(:));
% for nslice=1:size(PET,3)
%     figure(1)
%     imshow(PET(:,:,nslice),[])
%     h=title([' PET # ',num2str(nslice)]);
%     set(h,'FontWeight','bold')
%     colormap(jet)
%     colorbar
%     caxis([0 max1])
%     figure(2)
%     imshow(PET1(:,:,nslice),[])
%     h=title([' PET # ',num2str(nslice)]);
%     set(h,'FontWeight','bold')
%     colormap(jet)
%     colorbar
%     caxis([0 max1])
%     pause(0.05)
% end

%% info paciente 
ippCT=info_CT.ImagePositionPatient; %mm 
%ippPET=info_PET.ImagePositionPatient; %mm 
ippPET=[0,0,0]; 
vPET=[info_PET.PixelSpacing;info_PET.SliceThickness]; %mm

vCT=[info_PET.PixelSpacing;info_PET.SliceThickness];
%% CT Helicoidal 
%vCT=[info_CT.PixelSpacing;info_CT.SingleCollimationWidth/info_CT.SpiralPitchFactor]; %mm
%%
R_PET=imref3d(size(PET),[ippPET(1) ippPET(1)+vPET(1)*size(PET,1)],[ippPET(2) ippPET(2)+vPET(2)*size(PET,2)],[ippPET(3) ippPET(3)+vPET(3)*size(PET,3)]);
R_CT=imref3d(size(CT),[ippCT(1) ippCT(1)+vCT(1)*size(CT,1)],[ippCT(2) ippCT(2)+vCT(2)*size(CT,2)],[ippCT(3) ippCT(3)+vCT(3)*size(CT,3)]);

[optimizer, metric] = imregconfig('multimodal');

optimizer.InitialRadius=6e-14;
optimizer.MaximumIterations=1e3;

clc 
tranf = imregtform(PET, CT, 'affine', optimizer, metric,'DisplayOptimization',1,'PyramidLevels',3);
T=tranf.T;

[PET,R_PET]=imwarp(PET,R_PET,tranf,interp);%,'OutputView',imref3d(size(PET)));

 s=size(PET);
 nfig=100;
 figure(nfig)
 set(gcf,'Render','OpenGL')
 nfig=nfig+1;
 %max1=max(PET1(:));
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
     alpha 0.2
     pause(0.1)
end




s1=size(PET);
s=size(CT);

a=s./s1;

S=[a(1) 0   0 0 
    0  a(2) 0 0
    0  0    1 0
    0  0    0 1]; 

tranf1=affine3d(S); 
[PET,R_PET2]=imwarp(PET,R_PET,tranf1,interp);%,'OutputView',R_CT); %,intp,'FillValues',255);
clear PET1    

s=size(PET2);

PET3=zeros(size(CT));
PET3(1:s(1),1:s(2),1:s(3))=PET2;
PET3=uint16(PET3);
clear PET2
% s=size(PET1);
% PET3=zeros(size(CT));
% PET3(156:156+s(1)-1,156:156+s(2)-1,1:s(3))=PET1;
% PET3=uint16(PET3);
% clear PET2

max1=max(PET3(:));

% s=size(PET3);
% nfig=100;
% figure(nfig)
% set(gcf,'Render','OpenGL')
% nfig=nfig+1;
% %max1=max(PET1(:));
% for nslice=1:100
%     imshow(CT(:,:,nslice),[]);
%     h=title([' Fusion CT-SPECT # ',num2str(nslice)]);
%     set(h,'FontWeight','bold')
%     colormap(gray)
%     freezeColors;
%     hold on
%     imshow(PET3(:,:,nslice),[]);
%     %colormap(jet(16))
%     colormap(jet)
%     caxis([0 max1])
%     colorbar
%     alpha 0.2
%     pause(0.1)
%_s end

%% preguntar la reduccion 

%% generar un paciente_register

%%Ojo agregar el directorio generado 
f_save_tiff(PET3,1);
f_save_tiff(CT3,1);


% file='D:\MAT\3Dosim\pet.dcm';
% map=colormap(gray);
% uid = dicomuid;
% info_PET.SeriesInstanceUID = uid;
% dicomwrite(PET3(:,:,10),file,map,info_PET);

