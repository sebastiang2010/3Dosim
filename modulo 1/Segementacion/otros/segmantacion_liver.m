%% 
% agregar una pregunta para colocar la fuente
% incluirla como un indice de 255 y en la imagen 
%%
% Ojo cuando segmento hueso hay que ver que no sea higado o  tumor 
clear all 
close all 
clc 
%%
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
%
directorio=f_creo_directorio;
%%
index.aire=1;
index.skin=2;
index.blando=3;
index.liver=4;
index.hueso=5;
index.lung=6; 
index.tumor=10;
%% cargo tiff
tiff=1; %1 tiff 0 dicom
[I,~]=f_cargo_imagen(tiff);
I=squeeze(I);
%I=uint8(I); % para ver el aire de los pulmones

figure(1)
for i=1:size(I,3)
   imshow(I(:,:,i),[]);
   h=title(['Slice number # ',num2str(i)]);
   set(h,'FontWeight','bold')
   pause(0.05)
end
%% agrego binaria imagej para sacar el fondo 
[BW,~]=f_cargo_imagen(tiff);
BW=squeeze(BW);
fill_BW=zeros(size(BW));
for i=1:size(BW,3)
    [level,em] = graythresh(BW(:,:,i));
    BW(:,:,i) = im2bw(BW(:,:,i),level);
    fill_BW(:,:,i)=imfill(BW(:,:,i),'holes');
end

%BW=~BW;

figure(2)
for i=1:size(I,3)
   imshow(BW(:,:,i),[]);
   h=title(['Slice number # ',num2str(i)]);
   set(h,'FontWeight','bold')
   pause(0.05)
end

I=I.*fill_BW;
clear fill_BW
%% 
Phantom=zeros(size(I)); 
%% cargo el liver 
tiff=1; %1 tiff 0 dicom
[BW_liver,~]=f_cargo_imagen(tiff);
BW_liver=squeeze(BW_liver);
for i=1:size(BW_liver,3)
    [level,em] = graythresh(BW_liver(:,:,i));
    BW_liver(:,:,i) = im2bw(BW_liver(:,:,i),level);
end
%BW_liver=~BW_liver;
figure(3)
for i=1:size(I,3)
   imshow(BW_liver(:,:,i),[]);
   h=title(['Slice number # ',num2str(i)]);
   set(h,'FontWeight','bold')
   pause(0.05)
end

BW=BW.*~BW_liver;
% figure(4)
% for i=1:size(I,3)
%    imshow(BW(:,:,i),[]);
%    h=title(['Slice number # ',num2str(i)]);
%    set(h,'FontWeight','bold')
%    pause(0.2)
% end
Phantom=Phantom+BW_liver.*index.liver;
cell=unique(Phantom(:)); 

clear BW_liver 
%%
%% 
tiff=1; %1 tiff 0 dicom
[BW_tumor,~]=f_cargo_imagen(tiff);
BW_tumor=uint8(BW_tumor);
BW_tumor=squeeze(BW_tumor);
for i=1:size(BW_tumor,3)
    [level,em] = graythresh(BW_tumor(:,:,i));
    BW_tumor(:,:,i) = im2bw(BW_tumor(:,:,i),level);
end
%BW_tumor=~BW_tumor;
figure(5)
for i=1:size(I,3)
   imshow(BW_tumor(:,:,i),[]);
   h=title(['Slice number # ',num2str(i)]);
   set(h,'FontWeight','bold')
   pause(0.2)
end

BW=BW.*~BW_tumor;

% figure(60)
% for i=1:size(I,3)
%     imshow(BW(:,:,i),[])
%     pause(1)
% end

ind=BW_tumor==1; 
Phantom(ind)=index.tumor; 
cell=unique(Phantom(:)); 

clear BW_tumor 
%%
%close all
[hueso_ij,~]=f_cargo_imagen(tiff);
hueso_ij=squeeze(hueso_ij);

hueso_ij=hueso_ij.*BW;
hueso_ij=uint8(hueso_ij);
% 
% figure(70)
% for i=1:size(I,3)
%     imshow(hueso_ij(:,:,i),[])
%     pause(1)
% end

[I11,BW_hueso]=f_seg_hueso_1(hueso_ij);
Phantom=Phantom+BW_hueso.*index.hueso;
BW=BW.*~BW_hueso;

cell=unique(Phantom(:)); 

figure(6)
for i=1:size(I,3)
     imshow(BW(:,:,i));
     h=title(['Slice number # ',num2str(i)]);
     set(h,'FontWeight','bold')
     %caxis([1 10]) 
     %colormap(jet)
     pause(0.25)
end    

clear BW_hueso hueso_ij 
%% agrego tejido blando 
[Phantom]=f_seg_blando(BW,Phantom,index.blando);
cell=unique(Phantom(:)); 

%% cambio el indice al aire 
ind=find(Phantom==0);
Phantom(ind)=index.aire;
%%
figure(7)
for i=1:size(I,3)
     imshow(Phantom(:,:,i),[]);
     h=title(['Slice number # ',num2str(i)]);
     set(h,'FontWeight','bold')
     colormap(jet)
     caxis([1 10]) 
     pause(0.25)
end    
%% saco el aire que no va 
%[Phantom1,Ict,corte_aire]=f_saco_aire(Phantom1,Ict,index_aire,directorio); 

%% verificar que solo halla celdas index
% ok=-1; 
cell=unique(Phantom(:)); 
% %%index con la fuente
% %index=[index_aire index_skin index_blando index_hueso index_fuente];
% index=[index_aire index_skin index_blando index_hueso];
% n=length(index);
% if size(cell,1)>n 
%     disp('.......')
%     disp('NO SE SEGMENTO CORRECTAMENTE LA IMAGEN')
%     return
% else
%     a=0;
%     for i=1:length(cell)
%         if cell(i)==index(i);a=a+1;end
%     end
% end
% 
% 
% if a==n;ok=1;end  
% if ok==1;
%     disp('.......')
%     disp('Se segmento correctamente la imagen')
%     pause(1)
% else 
%     disp('.......')
%     disp('NO SE SEGMENTO CORRECTAMENTE LA IMAGEN')
%     pause(2)
%     return
% end
% %%
% clc 

file=[directorio,'/Phamton_mat.tif'];
delete(file);
for i=1:size(Phantom,3)
    imwrite(Phantom(:,:,i)./255,file,'tiff','WriteMode','append')
end
disp('.......')
disp('Se genero un tiff con la imagen segmentada en el directorio :')
disp(file)

%% guardo los datos en paciente
%paciente.index=index; 
%paciente.image_info=image_info(1); 
%paciente.s_o=size(I);
%paciente.s_new=size(Ict);
%paciente.reduccion=reduccion; 
%paciente.corte_aire=corte_aire; 
paciente.Phantom=uint8(Phantom);
paciente.I=uint8(I); 
paciente.index=index;


file=[directorio,'/paciente_1.mat'];
delete(file)
save(file,'paciente')

disp('.......')
disp('Se genero un archivo "paciente_1.mat" en el directorio :')
disp(file)


