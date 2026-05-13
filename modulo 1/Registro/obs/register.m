% Leer la información del volumen 
% grabar la fusion en dicom 
close all
clear 
clc
%% 
nshow=3;
nfig=1; 
%% agregar el path 
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
clear newpath currentdirectory
%%
directorio=f_creo_directorio;
%%
% [p,file_paciente,directorio_mat]=f_cargo_mat;
% if ~isempty(p)
%     paciente=p.paciente;
%     clear p 
% else 
%    directorio_mat=directorio;
% end 
%% 
interp='cubic';
%%
%dictionary = dicomdict('get');
tipo=0; % DICOM 
%
clc
disp(' ' )
disp(' Ingrese la Imagen PET');
[PET,info_PET,Rescale_PET]=f_cargo_imagen_v1(tipo);% 1 es tiff
PET=squeeze(PET);
PET=double(PET);
%chequear factor de calibracion 
% chequear units (BQML)
%% Bq/cm^3 -> Bq
PET=f_Rescale_Bq(PET,info_PET,Rescale_PET); %para pasar a Bq/ml
close all 
%%
figure(nfig)
nfig=nfig+1;
for i=1:size(PET,3)
    imshow(PET(:,:,i),[])
    colormap(jet)
    pause(0.1)
end 
disp(' Ingreso OK   ');
%% ingreso CT 
%chequear la modalidad 
disp(' ' )
disp(' Ingrese la Imagen CT');
[CT,info_CT,Rescale_CT]=f_cargo_imagen_v1(tipo);% 1 es tiff
CT=squeeze(CT);
CT=uint16(CT); 
figure(nfig)
nfig=nfig+1;
for i=1:size(CT,3)
    imshow(CT(:,:,i),[])
    colormap(gray)
    pause(0.1)
end 
disp(' Ingreso OK ');
%% info paciente 
ippCT=info_CT.ImagePositionPatient; %mm 
ippPET=info_PET.ImagePositionPatient; %mm 

vPET=[info_PET.PixelSpacing;info_PET.SliceThickness]; %mm
%CT Helicoidal 
%vCT=[info_CT.PixelSpacing;info_CT.SingleCollimationWidth/info_CT.SpiralPitchFactor]; %mm
%CT comun  
vCT=[info_CT.PixelSpacing;info_CT.SliceThickness]; 
vPET_org=vPET;

%% para normalizacion
n=sum(PET(:));
%% 
sPET=size(PET);
sCT=size(CT);

R_PET=imref3d(size(PET),[ippPET(1) ippPET(1)+vPET(1)*size(PET,1)],[ippPET(2) ippPET(2)+vPET(2)*size(PET,2)],[ippPET(3) ippPET(3)+vPET(3)*size(PET,3)]);
R_CT=imref3d(size(CT),[ippCT(1) ippCT(1)+vCT(1)*size(CT,1)],[ippCT(2) ippCT(2)+vCT(2)*size(CT,2)],[ippCT(3) ippCT(3)+vCT(3)*size(CT,3)]);

[optimizer, metric] = imregconfig('multimodal');

optimizer.InitialRadius=6e-14;
optimizer.MaximumIterations=1e3;

clc 
%tic 
tranf = imregtform(PET, CT, 'affine', optimizer, metric,'DisplayOptimization',1,'PyramidLevels',3);
T=tranf.T;
%time=toc; 

[PET1,R_PET1]=imwarp(PET,R_PET,tranf,interp);%,'OutputView',imref3d(size(PET)));
%%
if isempty(nshow);nshow=size(PET1,3);end

for i=1:size(CT,3)
    CT(:,:,i) = imadjust(CT(:,:,i),stretchlim(CT(:,:,i)),[]);
end

% figure(nfig)
% set(gcf,'Render','OpenGL')
% ax1=axes;
% ax2=axes; 
% nfig=nfig+1;
% max1=max(PET1(:));
% gray=colormap(gray); 
% jet=colormap(jet); 
% for nslice=1:nshow
%     imshow(CT(:,:,nslice),[],'parent',ax1,'colormap',gray);
%     colormap(gray)
%     imshow(PET1(:,:,nslice),[],'parent',ax2,'colormap',jet) ;
%     caxis([0 max1])
%     colorbar
%     alpha 0.4
%     P=get(ax2,'Position');
%     set(ax1,'Position',P);
%     h=title([' Fusion CT-PET # ',num2str(nslice)]);
%     set(h,'FontWeight','bold')
%     pause(0.01)
% end

%%
s=sCT./sPET;
s(2)=s(1); 
%s(3)=1;

S=[s(1) 0        0         0 
    0   s(1)     0         0
    0   0        s(3)      0
    0   0        0         1]; 

tranf1=affine3d(S); 
[PET2,R_PET2]=imwarp(PET1,R_PET1,tranf1,interp);

sPET2=size(PET2);
vPET2=vPET./s'; 

%% completo con ceros 
PET2=PET2(1:sCT(1),1:sCT(2),1:sCT(3));
%PET2(:,:,end:sCT(3))=0;

%% 
IND=PET2<0; 
PET2(IND)=0;

PET2=PET2./sum(PET2(:));
PET2=PET2.*n; 
 
%%
figure(nfig)
set(gcf,'Render','OpenGL')
ax1=axes;
ax2=axes; 
nfig=nfig+1;
max1=max(PET2(:));
gray=colormap(gray); 
jet=colormap(jet); 
for nslice=1:size(PET2,3)
    imshow(CT(:,:,nslice),[],'parent',ax1,'colormap',gray);
    colormap(gray)
    imshow(PET2(:,:,nslice),[],'parent',ax2,'colormap',jet) ;
    %colormap(jet(16))
    colormap(jet)
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
%PET2=uint16(PET2);
clc
f_save_tiff(PET2,1,directorio); %op=1 PET else CT
f_save_tiff(CT,0,directorio);

%if ~isempty(file_paciente);load(file_paciente);end
%% 
paciente.vCT=vCT;
paciente.vPET=vPET2; 
paciente.PET=PET2;
paciente.PET_original=PET; 
paciente.CT=CT;
paciente.info_CT=info_CT; 
paciente.info_PET=info_PET;
paciente.registro=1; 
paciente.registro_date=date;
paciente.PatientID=info_CT.PatientID; 
% OJO 
paciente.UnitsPET='Bq';
paciente.vPET_org=vPET_org;

%% save paciente 
file=[directorio,'/paciente.mat'];
delete(file)
save(file,'paciente')
 
disp(' ')
disp('....................................................................')
disp('....................................................................')
disp('    Se genero un archivo "paciente.mat" en el directorio:           ')
disp(' ')
disp(directorio)
