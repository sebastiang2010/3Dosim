%% 
% agregar una pregunta para colocar la fuente
% incluirla como un indice de 255 y en la imagen 
%%
%clear all 
close all 
clc 
%%
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
%
directorio=f_creo_directorio;
%%
index_aire=1;
index_skin=2;
index_blando=3;
index_hueso=4;
%index_fuente=0;
index_tumor=100; 

%% cargo tiff
% I=CT

disp(' ' )
disp('Ingrese la Imagen CT');
tiff=0; %1 tiff 0 dicom
[I,info_CT]=f_cargo_imagen(tiff);
I=squeeze(I);
%I=uint8(I); % para ver el aire de los pulmones

%I=f_HU(I,info_CT); 

disp(' ' )
disp('Ingrese la Imagen Tumor nii');
%cargo el tumor segmantado en mitk 
[tumor_nii]=f_cargar_nii; 


Tumor=uint8(tumor_nii.img); 
ind_tumor=Tumor==max(Tumor(:));
Tumor(ind_tumor)=index_tumor; 

% figure(1)
% for i=1:size(Tumor,3)
%    imshow(Tumor(:,:,i),[]);
%    h=title(['Slice number # ',num2str(i)]);
%    set(h,'FontWeight','bold')
%    pause(0.05)
% end


%% genero la matriz del fantoma
Phantom=zeros(size(I));
Phantom=uint8(Phantom);
%
% figure(2)
% for i=1:size(I,3)
%     imshow(I(:,:,i),[]);
%     title(['Slice number # ',num2str(i)]);
%     pause(0.1)
% end

% 
% figure(1)
% for i=1:size(CT,3)
%    imshow(CT(:,:,i),[]);
%    h=title(['Slice number # ',num2str(i)]);
%    set(h,'FontWeight','bold')
%    pause(0.05)
% end

% figure(5)
% imshow(CT(:,:,304),[]);


%% paso la imagen a binario 
%[I1,BW_skin,BW_fuente] =f_seg_piel(I);

%% Indico en el fantoma la piel
%Phantom1=Phantom1+BW_skin.*index_skin;
%Phantom1=Phantom1+BW_fuente.*index_fuente;
%cell=unique(Phantom1(:)); 

% figure(6)
% for i=1:size(I,3)
%     imshow(Phantom1(:,:,i),[])
%     colormap(jet)
%     title(['Slice number # ',num2str(i)]);
%     pause(0.5)
% end 
%
%close all
[I,BW_hueso]=f_seg_hueso_1(I);
Phantom1=Phantom1+BW_hueso.*index_hueso;


cell=unique(Phantom1(:)); %solo aire hueso y piel


close all
figure(500)
for i=1:size(I,3)
     imshow(Phantom1(:,:,i));
     h=title(['Slice number # ',num2str(i)]);
     set(h,'FontWeight','bold')
     caxis([1 4]) 
     colormap(jet)
     pause(0.25)
end    

%% agrego tejido blando 
[Phantom1] =f_seg_blando(I1,Phantom1,index_blando);
%close all 
cell=unique(Phantom1(:)); %todos

%% cambio el indice al aire 
ind=find(Phantom1==0);
Phantom1(ind)=index_aire;
%%
figure(600)
map=jet(length(cell));
for i=1:size(I,3)
     imshow(Phantom1(:,:,i),[]);
     h=title(['Slice number # ',num2str(i)]);
     set(h,'FontWeight','bold')
     colormap(map)
     caxis([1 4]) 
     pause(0.25)
end    


%% saco el aire que no va 
[Phantom1,Ict,corte_aire]=f_saco_aire(Phantom1,Ict,index_aire,directorio); 

%% verificar que solo halla celdas index
ok=-1; 
cell=unique(Phantom1(:)); 
%%index con la fuente
%index=[index_aire index_skin index_blando index_hueso index_fuente];
index=[index_aire index_skin index_blando index_hueso];
n=length(index);
if size(cell,1)>n 
    disp('.......')
    disp('NO SE SEGMENTO CORRECTAMENTE LA IMAGEN')
    return
else
    a=0;
    for i=1:length(cell)
        if cell(i)==index(i);a=a+1;end
    end
end


if a==n;ok=1;end  
if ok==1
    disp('.......')
    disp('Se segmento correctamente la imagen')
    pause(1)
else 
    disp('.......')
    disp('NO SE SEGMENTO CORRECTAMENTE LA IMAGEN')
    pause(2)
    return
end
%%
clc 

file=[directorio,'/Phamton_mat.tif'];
delete(file);
for i=1:size(I1,3)
    imwrite(Phantom1(:,:,i)./255,file,'tiff','WriteMode','append')
end
disp('.......')
disp('Se genero un tiff con la imagen segmentada en el directorio :')
disp(file)

%% guardo los datos en paciente
paciente.index=index; 
paciente.image_info=image_info(1); 
paciente.s_o=size(I);
paciente.s_new=size(Ict);
paciente.reduccion=reduccion; 
paciente.corte_aire=corte_aire; 
paciente.Phantom=uint8(Phantom1);
paciente.I=uint8(Ict); 


file=[directorio,'/paciente_1.mat'];
delete(file)
save(file,'paciente')

disp('.......')
disp('Se genero un archivo "paciente_1.mat" en el directorio :')
disp(file)

%%
% figure(200)
% imshow(Phantom1(:,:,3),[])
% colormap(map)

