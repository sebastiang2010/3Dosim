close all 
clc 
clear 
%% 
index.aire=1;
index.liver=90;
index.tejido_blando=30;
index.hueso=80; 
index.lung=50; 
index.tumor=100; %>100

%%
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
%%
directorio=f_creo_directorio;
%%
[p,file_paciente]=f_cargo_mat;
if ~isempty(p)
    paciente=p.paciente;
    clear p 
end 

% %% Cargo la imagen original 
if isfield(paciente,'CT')
     I=paciente.CT;
% else
%     tiff=0; %1 tiff 0 dicom
%     clc
%     disp(' ')
%     disp(' Ingrese la imagen CT a segmentar' )
%     
%     [I,image_info]=f_cargo_imagen(tiff);
%     I=squeeze(I);
 end
 
Phantom=zeros(size(I)); 

nslice=size(I,3); 

for i=1:nslice 
    I(:,:,i) = imadjust(I(:,:,i),stretchlim(I(:,:,i)),[]);
end 


for i=1:nslice
    figure(1)
    imshow(I(:,:,i),[])
    title(['Slice number # ',num2str(i)]);
    pause(0.1)
end 

%% OK
for i=1:nslice
    [BW_camilla] =f_saco_camilla(I(:,:,i)); % saco camillas y partes pequenas 
%     imshow(BW_camilla,[])
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)   
     I(:,:,i)=double(I(:,:,i)).*double(~BW_camilla); % sin camilla        
end 



clear BW_camilla
for i=1:nslice
    figure(1)
    imshow(I(:,:,i),[])
    title(['Slice number # ',num2str(i)]);
    pause(0.1)
end

% % saco aire_periferico OK 
% for i=1:nslice 
%     [bw_s_aire] =f_saco_aire(I(:,:,i)); % saco aire
%     figure(500)
%     imshow(bw_s_aire,[])
%     I(:,:,i)=double(I(:,:,i)).*double(bw_s_aire); % sin camilla       
% end 
% clear bw_s_aire; 
% 
% for i=1:nslice 
%     figure(2)
%     imshow(I(:,:,i),[])
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)
% end

for i=1:nslice
    [BW_body] =f_sin_aire_exterior(I(:,:,i)); % saco camillas y partes pequenas 
%     imshow(BW_camilla,[])
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)   
     I(:,:,i)=double(I(:,:,i)).*double(BW_body); 
     IND_aire=BW_body==0;
     IND_tejido_blando=BW_body==1; 
     A=Phantom(:,:,i);
     A(IND_aire)=index.aire; 
     A(IND_tejido_blando)=index.tejido_blando; 
     Phantom(:,:,i)=A;
     
end 



corte=0; 
for i=1:nslice 
   
    [bw_lung,bw_intestino,corte]=f_saco_lung(I(:,:,i),corte); 
    
%     figure(500)
%     imshowpair(bw_lung,bw_intestino,'montage')
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)
    
       
    I(:,:,i)=double(I(:,:,i)).*double(~bw_lung); %saco de la imagen  
    I(:,:,i)=double(I(:,:,i)).*double(~bw_intestino); % saco de la imagen
    IND_lung=bw_lung==1; 
    IND_intestino=bw_intestino==1; 
    A=Phantom(:,:,i);
    A(IND_lung)=index.lung; 
    A(IND_intestino)=index.aire; 
    Phantom(:,:,i)=A;
end
%a=unique(Phantom); 
clear bw_lung bw_intestino
max_Phantom=max(Phantom(:)); 
figure(2)
for i=1:nslice
    imshow(Phantom(:,:,i),[])
    title(['Slice number # ',num2str(i)]);
    colormap(jet)
    clim(gca, [0 max_Phantom]);
    pause(0.1)
end 

%% saco hueso
% tic 
% for i=1:nslice 
%     %if i==1 
%      %  J = histeq(I(:,:,159)); 
%      %  imshow(J,[]) 
%       % imcontrast(gca);
%     %end 
%     
%     %J= imadjust(J,[60000/65535 1],[]);
%     [BW_hueso] =f_saco_hueso(I(:,:,i)); % saco hueso 
%     
%     figure(500)
%     imshow(BW_hueso,[])
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)
%     
%     I(:,:,i)=double(I(:,:,i)).*double(~BW_hueso); % sin camilla
%     Phantom(:,:,i)=Phantom(:,:,i)+BW_hueso.*index.hueso;     
% end
%time=toc; 
%a=unique(Phantom);
%clear BW_hueso
% figure(2) 
% for i=1:nslice
%     imshowpair(I(:,:,i),Phantom(:,:,i),'montage')
%     %imshow(I(:,:,i),[])
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)
%  end 


% figure(2)
% for i=1:nslice
%     imshowpair(I(:,:,i),Phantom(:,:,i),'montage')
%     %imshow(I(:,:,i),[])
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)
% end 

%% cargar liver 
%a=unique(Phantom); 
% esto estaba para MITK 
% hay que modificarlo para el 3Dslicer 
% agregar como TIff que ya lo tengo 


clc 
disp(' ')
disp(' Ingrese la imagen del higado')

angle=90; 

liver=f_cargar_nii;
A=liver.img; 
A=uint8(A); 
A=f_flip(A,1);

A=imbinarize(A);

se = strel('square',10);
for i=1:nslice
   A(:,:,i)=imfill(A(:,:,i),4,'holes');
   %A(:,:,i)=imdilate(A(:,:,i),se);
   A(:,:,i)=imrotate(A(:,:,i),angle);
end 

IND_liver=A==1;
I(IND_liver)=0; 

Phantom(IND_liver)=index.liver; 

%a=unique(Phantom); 
clear liver A
% 
% for i=1:nslice
%     imshowpair(I(:,:,i),Phantom(:,:,i),'montage')
%     %imshow(liver.img(:,:,i),[])
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)
% end 

%% cargar tumor 
%agregar un while 
clc 
disp(' ')
disp(' Ingrese la imagen del tumor')

angle=90; 

tumor=f_cargar_nii;

A=tumor.img; 
A=uint8(A); 
A=f_flip(A,1); % 


A=imbinarize(A);

for i=1:nslice
   A(:,:,i)=imfill(A(:,:,i),4,'holes');
   A(:,:,i)=imdilate(A(:,:,i),se);
   A(:,:,i)=imrotate(A(:,:,i),angle);
end 

IND_tumor=A==1;
I(IND_tumor)=0; %saco de la imagen CT 


%Phantom=Phantom+double(A); 
Phantom(IND_tumor)=index.tumor; 

% for i=1:nslice
%     imshowpair(I(:,:,i),Phantom(:,:,i),'montage')
%     %imshow(tumor.img(:,:,i),[])
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)
% end 

%% 

max_Phantom=max(Phantom(:)); 
figure(2)
for i=1:nslice
    imshow(Phantom(:,:,i),[])
    title(['Slice number # ',num2str(i)]);
    colormap(jet)
    clim(gca, [0 max_Phantom]);
    pause(0.1)
end 

%% chequeo que este bien segmentado 
a=unique(Phantom); 

%% grabo Tiff
f_save_tiff(Phantom,2,directorio); %op=0 CT op=1 PET op=2 Phantom  
%% 
% if ~isempty(file_paciente)
%     load(file_paciente);
% else 
%     file_paciente=[directorio,'/paciente.mat'];
% end

paciente.Phantom=uint8(Phantom);
paciente.segmentado=1; 
paciente.index=index; 

file=[directorio,'/paciente.mat'];
delete(file)
save(file,'paciente')

disp(' ')
disp('....................................................................')
disp('....................................................................')
disp('    Se genero un archivo "paciente.mat" en el directorio:           ')
disp(' ')
disp(directorio)