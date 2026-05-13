%% generar un paciente_register
% version 04/04/18
%clear all
close all
clear 
clc
%% ojo ver la que la suma de activida se conserva
nshow=[];
nfig=1; 
%% agregar el path 
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
clear newpath currentdirectory
%%
directorio=f_creo_directorio;
%%
% [p,file_paciente]=f_cargo_mat;
% if ~isempty(p)
%     paciente=p.paciente;
%     clear p 
% end 
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
PET=double(PET);
%chequear factor de calibracion 
% chequear units (BQML)
disp('Ingreso OK   ');

% for i=1:size(PET,3)
%         imshow(PET(:,:,i),[])
%         pause(0.1)
% end 

n=sum(PET(:));

%% chequear la modalidad 
disp(' ' )
disp('Ingrese la Imagen CT');
[CT,info_CT]=f_cargo_imagen(tipo);% 1 es tiff
CT=squeeze(CT);
CT=uint16(CT); 
disp('Ingreso OK ');
% 
% for i=1:size(CT,3)
%         imshow(CT(:,:,i),[])
%         pause(0.1)
% end

%% 
%helperVolumeRegistration(CT,PET);
%% pasaje a HU %%hacer funcion 
%CT=f_HU(CT,info_CT); 
%PET=f_HU(PET,info_PET); %para pasar a Bq/ml  
close all 

%% info paciente 
ippCT=info_CT.ImagePositionPatient; %mm 
ippPET=info_PET.ImagePositionPatient; %mm 

vPET=[info_PET.PixelSpacing;info_PET.SliceThickness]; %mm
%CT Helicoidal 
vCT=[info_CT.PixelSpacing;info_CT.SingleCollimationWidth/info_CT.SpiralPitchFactor]; %mm
%CT comun  
%vCT=[info_CT.PixelSpacing;info_CT.SliceThickness]; 

sPET=size(PET);
sCT=size(CT);

R_PET=imref3d(size(PET),[ippPET(1) ippPET(1)+vPET(1)*size(PET,1)],[ippPET(2) ippPET(2)+vPET(2)*size(PET,2)],[ippPET(3) ippPET(3)+vPET(3)*size(PET,3)]);
R_CT=imref3d(size(CT),[ippCT(1) ippCT(1)+vCT(1)*size(CT,1)],[ippCT(2) ippCT(2)+vCT(2)*size(CT,2)],[ippCT(3) ippCT(3)+vCT(3)*size(CT,3)]);

[optimizer, metric] = imregconfig('multimodal');

optimizer.InitialRadius=6e-14;
optimizer.MaximumIterations=1e3;

clc 
tic 
tranf = imregtform(PET, CT, 'affine', optimizer, metric,'DisplayOptimization',1,'PyramidLevels',3);
T=tranf.T;
time=toc; 

[PET1,R_PET1]=imwarp(PET,R_PET,tranf,interp);%,'OutputView',imref3d(size(PET)));

%PET1=PET1(1:sPET(1),1:sPET(2),1:sPET(3));

if isempty(nshow);nshow=size(PET1,3);end

figure(nfig)
set(gcf,'Render','OpenGL')
ax1=axes;
ax2=axes; 
nfig=nfig+1;
max1=max(PET1(:));
gray=colormap(gray); 
jet=colormap(jet); 
for nslice=1:nshow
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

%sPET=size(PET1); 

s=sCT./sPET;


S=[s(1) 0         0         0 
    0   s(1)      0         0
    0   0         s(3)      0
    0   0         0         1]; 

tranf1=affine3d(S); 
[PET2,R_PET2]=imwarp(PET1,R_PET1,tranf1,interp);%,'OutputView',R_CT); %,intp,'FillValues',255);


figure(nfig)
set(gcf,'Render','OpenGL')
ax1=axes;
ax2=axes; 
nfig=nfig+1;
max1=max(PET2(:));
gray=colormap(gray); 
jet=colormap(jet); 
for nslice=1:nshow
    imshow(CT(:,:,nslice),[],'parent',ax1,'colormap',gray);
    %colormap(gray)
    %freezeColors;
    %hold on
    imshow(PET2(:,:,nslice),[],'parent',ax2,'colormap',jet) ;
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


%PET3=zeros(sCT); 
PET3=PET2(1:sCT(1),1:sCT(2),1:sCT(3));


% chequear que este igual que el original  
IND=PET3<0; 
PET3(IND)=0;

PET3=PET3./sum(PET1(:));
PET3=PET3.*n; 

figure(nfig)
set(gcf,'Render','OpenGL')
ax1=axes;
ax2=axes; 
nfig=nfig+1;
max1=max(PET3(:));
gray=colormap(gray); 
jet=colormap(jet); 
for nslice=1:size(PET3,3)
    imshow(CT(:,:,nslice),[],'parent',ax1,'colormap',gray);
    %colormap(gray)
    %freezeColors;
    %hold on
    imshow(PET3(:,:,nslice),[],'parent',ax2,'colormap',jet) ;
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

% % save tiff
% f_save_tiff(PET2,1,directorio); %op=1 PET else CT
% f_save_tiff(CT,0,directorio);
% 
% if ~isempty(file_paciente);load(file_paciente);end
% 
% paciente.tvoxel=tvoxel;
% paciente.PET=PET2; 
% paciente.CT=CT;
% paciente.info_CT=info_CT; 
% paciente.info_PET=info_PET;
% paciente.registro=1; 
% paciente.registro_date=date;
% paciente.PatientIDtientID=info_CT.PatientID; 
% 
% file=[directorio,'/paciente.mat'];
% delete(file)
% save(file,'paciente')
% 
% 
nslice=70;
figure(100)
%subplot(2,2,1)
set(gcf,'Render','OpenGL')
ax1=axes;
ax2=axes; 
nfig=nfig+1;
max1=max(PET1(:));
gray=colormap(gray); 
jet=colormap(jet); 
%figure(100)
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
%nslice=24;
figure(101)
set(gcf,'Render','OpenGL')
%subplot(2,2,2)
ax1=axes;
ax2=axes; 
nfig=nfig+1;
max1=max(PET3(:));
gray=colormap(gray); 
jet=colormap(jet); 
%figure(100)
imshow(CT(:,:,nslice),[],'parent',ax1,'colormap',gray);
%colormap(gray)
%freezeColors;
%hold on
imshow(PET3(:,:,nslice),[],'parent',ax2,'colormap',jet) ;
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

