%%% 
%% 
%I=Phantoma 
%%
%%
tic 
clear 
close all 
clc
%% 3Dosim 
version='2.4'; 
% Modificado 07/03/18
%% parametros
nshow=[];
%nshow=10;
nfig=1; 
%op_fuente=2; %Y-90
flipz=0; % hacer una funcion 
flip=1; 
tmesh=[1,1];% tmesh(1)=1 tally 1 // tmesh(2)=1 tally 3
%% hacer funcion 
prefs.ImshowBorder='loose';
prefs.ImshowAxesVisible='off'; 
prefs.ImshowInitialMagnification='fit';
prefs.ImtoolStartWithOverview=0; 
prefs.ImtoolInitialMagnification='adaptive';
prefs.UseIPPL=1;
iptsetpref('ImshowBorder',prefs.ImshowBorder);
iptsetpref('ImshowInitialMagnification',prefs.ImshowInitialMagnification);
%% agregar el path 
currentdirectory=pwd;
newpath=[currentdirectory,'\funciones']; 
path(path,newpath)
clear newpath currentdirectory
%% funcion creo directorio
directorio=f_creo_directorio;
%% cargo mat ojo no se puede por ahora cambiar el nombre del archivo
% agregar tvoxel 
[p,file_paciente,directorio1]=f_cargo_mat;
if ~isempty(p)
    paciente=p.paciente;
    clear p archivo
    % Ojo que Uso I para el fantoma
    
    
    if isfield(paciente,'registro')
        if paciente.registro==1;ok(1)=1;end
    else
        disp(' ')
        disp(' Las imagenes no estan registradas' )
        return
    end
    if isfield(paciente,'segmentado')
        if paciente.segmentado==1;ok(2)=1;end
    else
        disp(' ')
        disp(' Las imagenes no esta segmentada' )
        return
    end
else
    disp(' ')
    disp(' Debe ingresar paciente.mat' )
    
    return
end
I=uint8(paciente.Phantom);
CT=paciente.CT; 
PET=paciente.PET; 
tvoxel=paciente.tvoxel; % mmm 
index=paciente.index; 
PatientID=paciente.PatientID; 

clear paciente 

I=zeros(6,6,4);

%I(i,j,k)
I(1:end/2,1:end/2,:)=index.aire;
I(1:end/2,end/2+1:end,:)=index.lung;
I(end/2+1:end,1:end/2,:)=index.hueso;
I(end/2+1:end,end/2+1:end,:)=index.liver;

PET=zeros(6,6,4);

PET(3:4,3:4,2)=1;
a=sum(PET(:));
%PET=PET./a; 


%imtool(P(:,:,3))

tvoxel=ones(1,3)*10; 
tvoxel2=ones(1,3)*1;

s=tvoxel./tvoxel2;

S=[ s(1)  0     0     0
    0   s(2)    0     0  
    0     0     s(3)  0
    0     0     0     1]; 

tform = affine3d(S);
PET1=PET;
PET=imwarp(PET1,tform,'cubic');

%imtool(P1(:,:,20))
IND=PET<0; 
PET(IND)=0; 
PET=PET.*a/sum(PET(:));

%figure(3)
%imshow(P2(:,:,4),[])
%imtool(P2(:,:,4))

%b=sum(P2(:));

I=zeros(60,60,40);
I(1:30,1:30,:)=index.aire;
I(1:30,31:60,:)=index.lung;
I(31:60,1:30,:)=index.hueso;
I(31:60,31:60,:)=index.liver;

tvoxel=tvoxel2; 

%% genero el archivo de MCNP
name='3Dosim_MCNP.i';
archivo=[directorio1,'\',name];
%achivo=file_paciente; 
fid=fopen(archivo, 'w+');
status=fclose(fid);
if status==0
    %clc
    disp('  ')   
    disp(' El archivo se creo correctamente')
else
    disp(' ')
    disp(' EL ARCHIVO NO SE CREO CORRECTAMENTE')
    return 
end
clear status directorio dirctorio1 

%%
if isempty(nshow);nshow=size(I,3);end

%% 
figure(1)
set(gcf,'Render','OpenGL')
ax1=axes;
ax2=axes; 
%nfig=nfig+1;
max1=max(PET(:));
gray=colormap(gray); 
jet=colormap(jet); 
for nslice=1:nshow
    imshow(CT(:,:,nslice),[],'parent',ax1,'colormap',gray);
    %colormap(gray)
    %freezeColors;
    %hold on
    imshow(PET(:,:,nslice),[],'parent',ax2,'colormap',jet) ;
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
close all 
%% Genero los materiales
mat=f_materiales;
%% Genero las fuentes
fuentes=f_fuentes;
%% busco la cantidad de celdas. 
%cell=unique(I(:)); %da igual al algoritmo que yo desarrolle. 
%% por las dudas verifico el que no halla ceros
ind=I==0;
I(ind)=index.aire;
clear ind 
%% calculo nuevamente el numero de celdas
cell=unique(I(:));
%% asigno los materiales
IdMat=f_selc_mat(cell,index);

%% recorte  colorcar en una funcion 

recorte=f_recorto(I,index.liver,nshow); % lo realiza en forma automatica

if ~isempty(recorte)
    %recorte=[ymin ymax xmin xmax]
    I1=I(recorte(1):recorte(2),recorte(3):recorte(4),:);
    PET1=PET(recorte(1):recorte(2),recorte(3):recorte(4),:);
    CT1=CT(recorte(1):recorte(2),recorte(3):recorte(4),:);
else
    I1=I;
    PET1=PET;
    CT1=CT;
end

clear PET I CT
%% 
close all 
%% Es necesario 1
[x,y,z]=size(I1);
image_size=[y,x,z]; %MCNP
clear x y z 
%clear method ok
%% flipeo para generar la geometria
I1=f_flip(I1,flip); 
PET1=f_flip(PET1,flip); 
%% realizar un recorte de aire
%% genero el titulo 
f_genero_titulo(archivo,version,PatientID);
clear version 
%% generio los universos 
f_genero_geometria(cell,mat,archivo,image_size,IdMat,flip); 
%% pregunto del tamano del voxel 
tvoxel=f_tvoxel(tvoxel);
%% genero el voxel 
tic 
f_genero_voxel_1(I1,archivo); 
time.voxel=toc;
%% Genero la geometria final %Superficies
f_genero_geometria_final(archivo,image_size,tvoxel); 
%% Mode
[mode,max_e]=f_mode(archivo,tvoxel,fuentes); 
%% Genero la fuente
tic
corteN=0; 
f_genero_fuente_3_v2(archivo,tvoxel,cell,I1,PET1,fuentes,corteN);
time.fuente=toc;
%% genero el mesh tally   
tally_ver=f_genero_tally(archivo,tvoxel,image_size,cell,max_e,tmesh,PatientID); 
%% wwg 
%pos_fuente_2=find(SPECT~=0);
%f_g_wwg(archivo,pos_fuente_2,s_new,tvoxel);
%% agrego los materiales 
f_genero_materiales(mat,archivo,IdMat);
%% imprime y la generacion del mctall
f_g_rand_dbcn(archivo);
%% 
f_g_print(archivo); 
%% genero el numero de particulas
status=f_g_numero_part(archivo);
%fclose(fid); % se cierra en cada funcion 
if status==0 
    clc
    disp(' ')
    disp([' El archivo MCNP: ',name,' se genero correctamente en directorio: '])
    disp(archivo)
else
    disp(' EL ARCHIVO NO SE GENERO')
end 
%%
time.total=toc;
%% grabo la estructura paciente
%if flipz==1;PET=PET(:,:,end:-1:1);end  
if ~isempty(file_paciente);load(file_paciente);end

densidad=zeros(1,length(cell));
for i=1:length(cell) 
    densidad(i)=mat(IdMat(i),1).Densidad;
end

paciente.tvoxel=tvoxel;
paciente.mode=mode;
paciente.flip=flip;
paciente.flipz=flipz; %para PET
paciente.IdMAT=IdMat'; 
paciente.densidad=densidad'; %g/cm^3
% no es  necesario electrones sum_emisividad=1
%paciente.sum_emisividad=sum_emisividad;
paciente.cell=cell; 
paciente.tally_ver=tally_ver;
%paciente.Phantom=I; 
%paciente.PET=PET; 
paciente.corteN=corteN;
paciente.time=time;
paciente.recorte=recorte; 
paciente.tmesh=tmesh;
paciente.index=index;
paciente.mcncp=1; 
paciente.PET=PET1;
paciente.Phantom=I1;

%file=[directorio,'/paciente.mat'];
delete(file_paciente)
save(file_paciente,'paciente')

disp(' ')
disp('Se genero un archivo "paciente.mat" en el directorio: ')
disp(file_paciente)

