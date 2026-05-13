%% generar un paciente_register
% version 16/02/18
%clear all
close all
clear 
clc
%% agregar el path 
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
clear newpath currentdirectory
%%
directorio=f_creo_directorio;
%%
[p,file_paciente]=f_cargo_mat;
if ~isempty(p)
    paciente=p.paciente;
    clear p 
end
if ~isempty(file_paciente)
    load(file_paciente);
else 
    file_paciente=[directorio,'/paciente.mat'];
end
%%
interp='cubic';
%%
%dictionary = dicomdict('get');
tipo=0; 
clc
disp(' ' )
disp('Ingrese la Imagen PET');
[PET,info_PET]=f_cargo_imagen(tipo);% 1 es tiff
PET=squeeze(PET);
%chequear factor de calibracion 
% chequear units (BQML)
disp('Ingreso OK   ');

%% chequear la modalidad 
disp(' ' )
disp('Ingrese la Imagen CT');
[CT,info_CT]=f_cargo_imagen(tipo);% 1 es tiff
CT=squeeze(CT);
CT=uint16(CT); 
disp('Ingreso OK ');

% %%
% for i=1:size(CT,3)
%     imshow(CT(:,:,i),[])
%     pause(0.1)
% end 
% 
% for i=1:size(PET,3)
%     imshow(PET(:,:,i),[])
%     pause(0.1)
%     colormap(jet)
% end 

%% 
%helperVolumeRegistration(CT,PET);
%% pasaje a HU %%hacer funcion 
%CT=f_HU(CT,info_CT); 
%PET=f_HU(PET,info_PET); %para pasar a Bq/ml  

%% info paciente 
ippCT=info_CT.ImagePositionPatient; %mm 
% ippPET=info_PET.ImagePositionPatient; %mm no ests esta info 

vPET=[info_PET.PixelSpacing;info_PET.SliceThickness]; %mm
%CT Helicoidal 
%vCT=[info_CT.PixelSpacing;info_CT.SingleCollimationWidth/info_CT.SpiralPitchFactor]; %mm
vCT=[info_CT.PixelSpacing;info_CT.SliceThickness];

%R_PET=imref3d(size(PET),[ippPET(1) ippPET(1)+vPET(1)*size(PET,1)],[ippPET(2) ippPET(2)+vPET(2)*size(PET,2)],[ippPET(3) ippPET(3)+vPET(3)*size(PET,3)]);
R_CT=imref3d(size(CT),[ippCT(1) ippCT(1)+vCT(1)*size(CT,1)],[ippCT(2) ippCT(2)+vCT(2)*size(CT,2)],[ippCT(3) ippCT(3)+vCT(3)*size(CT,3)]);

[optimizer, metric] = imregconfig('multimodal');

optimizer.InitialRadius=6e-14;
optimizer.MaximumIterations=1e3;

clc 
tic 
tranf = imregtform(PET, CT, 'affine', optimizer, metric,'DisplayOptimization',1,'PyramidLevels',3);
T=tranf.T;
time=toc; 

%[PET,R_PET]=imwarp(PET,R_PET,tranf,interp);%,'OutputView',imref3d(size(PET)));

s1=size(PET);
s=size(CT);

tvoxel=s./s1;
tvoxel=round(tvoxel,2);
tvoxel(2)=tvoxel(1); 
clear s s1

S=[tvoxel(1) 0   0 0 
    0  tvoxel(2) 0 0
    0  0        1 0
    0  0        0 1]; 

tranf1=affine3d(S); 
[PET]=imwarp(PET,tranf1,interp);%,'OutputView',R_CT); %,intp,'FillValues',255);
    

s=size(PET);

PET1=zeros(size(CT));
PET1(1:s(1),1:s(2),1:s(3))=PET;
PET1=uint16(PET1);
clear PET

%helperVolumeRegistration(PET,CT);
%%
figure(1)
set(gcf,'Render','OpenGL')
ax1=axes;
ax2=axes; 
%nfig=nfig+1;
max1=max(PET1(:));
gray=colormap(gray); 
jet=colormap(jet); 
for nslice=1:s(3)
    imshow(CT(:,:,nslice),[],'parent',ax1,'colormap',gray);
    %colormap(gray)
    %freezeColors;
    %hold on
    imshow(PET1(:,:,nslice),[],'parent',ax2,'colormap',jet) ;
    %colormap(jet(16))
    %colormap(jet)
    caxis([0 max1])
    colorbar
    alpha 0.4
    P=get(ax2,'Position');
    set(ax1,'Position',P);
    h=title([' Fusion CT-PET # ',num2str(nslice)]);
    set(h,'FontWeight','bold')
    pause(0.01)
end


%% save tiff
f_save_tiff(PET1,1,directorio); %op=1 PET else CT
f_save_tiff(CT,0,directorio);

%% 
paciente.tvoxel=tvoxel;
paciente.PET=PET1; 
paciente.CT=CT;
paciente.info_CT=info_CT; 
paciente.info_PET=info_PET;
paciente.registro=1; 


delete(file_paciente)
save(file_paciente,'paciente')




