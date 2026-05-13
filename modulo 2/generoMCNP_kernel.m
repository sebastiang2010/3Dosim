%%% 
%% 
%I=Phantoma 
%%
% la fuente utiliza el vPET
%%
tic 
clear 
close all 
clc
%% 3Dosim 
version='3.01'; 
%% parametros
%nshow=[];
nshow=10;
nfig=1; 
%op_fuente=2; %Y-90
% OJo que en liver no queda bien los tally de verificacion 
n_liver=0; %numero de tallies de verificacion 
n_tumor=0; %numero de tallies de verificacion 
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
I1=uint8(paciente.Phantom);
CT1=paciente.CT;
PET1=paciente.PET_intp.PET;
vCT=paciente.vCT; %mmm Antes y en las funciones tvoxel
vPET=paciente.PET_intp.vPET;% mmm
index=paciente.index;
PatientID=paciente.PatientID;
R_PET=paciente.PET_intp.R_PET; 
R_CT=paciente.R_CT; 

% for i=1:size(I,3)
%     imshow(I(:,:,i),[]);
%     pause(0.1) 
% end 
%ind=I==1; 
%I(ind)=0; 


%clear paciente 
%% genero el archivo de MCNP
name='3Dosim_MCNP_Y90.i';
directorio='C:\MAT\3Dosim\';
archivo=[directorio1,name];
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
if isempty(nshow);nshow=size(I1,3);end

%% 
% figure(nfig)
% nfig=nfig+1;
% set(gcf,'Render','OpenGL')
% ax1=axes;
% ax2=axes; 
% %nfig=nfig+1;
% max1=max(PET1(:));
% gray=colormap(gray); 
% jet=colormap(jet); 
% for nslice=1:nshow
%     imshow(CT1(:,:,nslice),[],'parent',ax1,'colormap',gray);
%     %colormap(gray)
%     %freezeColors;
%     %hold on
%     imshow(PET1(:,:,nslice),[],'parent',ax2,'colormap',jet) ;
%     %colormap(jet(16))
%     %colormap(jet)
%     caxis([0 max1])
%     colorbar
%     alpha 0.4
%     P=get(ax2,'Position');
%     set(ax1,'Position',P);
%     h=title([' Fusion CT-PET # ',num2str(nslice)]);
%     set(h,'FontWeight','bold')
%     pause(0.01)
% end

% figure(nfig)
% ax2=axes; 
% nfig=nfig+1;
% %max1=max(PET1(:));
% %gray=colormap(gray); 
% jet=colormap(jet); 
% for nslice=1:nshow
%     imshow(I1(:,:,nslice),[])
%     %colormap(gray)
%     colormap(jet)
%     %freezeColors;
%     %hold on
%     %imshow(PET1(:,:,nslice),[],'parent',ax2,'colormap',jet) ;
%     %colormap(jet(16))
%     %colormap(jet)
%     %caxis([0 max1])
%     %colorbar
%     %alpha 0.4
%     %P=get(ax2,'Position');
%     %set(ax1,'Position',P);
%     h=title([' Fusion CT-PET # ',num2str(nslice)]);
%     set(h,'FontWeight','bold')
%     pause(0.01)
% end
%close all 
%% Genero los materiales
mat=f_materiales;
%% Genero las fuentes
fuentes=f_fuentes;
%% busco la cantidad de celdas. 
%cell=unique(I(:)); %da igual al algoritmo que yo desarrolle. 
%% por las dudas verifico el que no halla ceros
ind=I1==0;
I1(ind)=index.aire;
clear ind 
%% calculo nuevamente el numero de celdas
cell=unique(I1(:));
%% asigno los materiales
IdMat=f_selc_mat(cell,index);

%% recorte  colorcar en una funcion 
%recorte=f_recorto(I,index.liver,nshow); % lo realiza en forma automatica
%if ~isempty(recorte)
    %recorte=[ymin ymax xmin xmax]
%    I1=I(recorte(1):recorte(2),recorte(3):recorte(4),:);
%    PET1=PET(recorte(1):recorte(2),recorte(3):recorte(4),:);
%    CT1=CT(recorte(1):recorte(2),recorte(3):recorte(4),:);
% else
%    I1=I;
%    PET1=PET;
%    CT1=CT;
%end

%clear PET I CT  
%% 
%close all 
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
% pregunto del tamano del voxel 
%tvoxel=f_tvoxel(tvoxel);
%% genero el voxelizado  
tic 
f_genero_voxel_1(I1,archivo); 
time.voxel=toc;
%% Genero la geometria final %Superficies
f_genero_geometria_final(archivo,image_size,vCT); 
%% Mode
[mode,max_e]=f_mode(archivo,fuentes); 
%% Genero la fuente
tic
corteN=100; 
f_genero_fuente_3_v2(archivo,vPET,cell,I1,PET1,fuentes,corteN) 
%f_genero_fuente_3_v3(archivo,vPET,PET1,fuentes,corteN,R_PET,R_CT);
time.fuente=toc;
%% genero el mesh tally   
tally_ver=f_genero_tally(archivo,vCT,image_size,cell,max_e,tmesh,PatientID,I1,index,n_liver,n_tumor); 
%% wwg 
%pos_fuente_2=find(SPECT~=0);
%f_g_wwg(archivo,pos_fuente_2,s_new,tvoxel);
%% agrego los materiales 
f_genero_materiales(mat,archivo,IdMat);
%% imprime y la generacion del mctall
f_g_rand_dbcn(archivo);
%% 
max2=100000; % numero de particulas para ver defoult max=10000 
f_g_print(archivo,max2); 
%% genero el numero de particulas
status=f_g_numero_part(archivo);
%fclose(fid); % se cierra en cada funcion 
if status==0 
    clc
    disp(' ')
    disp(['El archivo MCNP: ',name,' se genero correctamente en directorio: '])
    disp(archivo)
else
    disp('EL ARCHIVO NO SE GENERO')
end 
%% 
% figure(nfig)
% nfig=nfig+1; 
% set(gcf,'Render','OpenGL')
% [xr, yr, zr, imr] = reducevolume(I1, [2 2 1]);
% imr=smooth3(imr,'gaussian');
% 
% p=patch(isosurface(xr,yr,zr,imr,index.liver));
% isonormals(xr,yr,zr,imr,p);
% 
% % higado 
% transparency=0.2;
% set(p,'EdgeColor','none');
% set(p,'FaceColor','blue')
% set(p,'EdgeColor','none')
% set(p,'FaceAlpha',transparency)
% 
% % tumor 
% p=patch(isosurface(xr,yr,zr,imr,index.tumor));
% isonormals(xr,yr,zr,imr,p);
% 
% transparency=1;
% set(p,'EdgeColor','none');
% set(p,'FaceColor','r'); 
% set(p,'EdgeColor','none');
% set(p,'FaceAlpha',transparency);
% 
% x=1/vCT(1);
% y=1/vCT(2);
% z=1/vCT(3);
% az=-37.5; %view(3) 
% el=30;
% daspect([x y z]); 
% view(az,el);
% camlight; 
% lighting phong
% 
% hold on 
% h=scatter3(tally_ver(1:n_liver,2),tally_ver(1:n_liver,1),tally_ver(1:n_liver,3));
% set(h,'MarkerFaceColor','g')
% 
% figure(nfig)
% nfig=nfig+1; 
% set(gcf,'Render','OpenGL')
% p=patch(isosurface(xr,yr,zr,imr,index.tumor));
% isonormals(xr,yr,zr,imr,p);
% 
% transparency=0.5;
% set(p,'EdgeColor','none');
% set(p,'FaceColor','r'); 
% set(p,'EdgeColor','none');
% set(p,'FaceAlpha',transparency);
% 
% x=1/vCT(1);
% y=1/vCT(2);
% z=1/vCT(3);
% az=-37.5; %view(3) 
% el=30;
% daspect([x y z]); 
% view(az,el);
% camlight; 
% lighting phong
% hold on 
% h=scatter3(tally_ver(n_liver+1:end,2),tally_ver(n_liver+1:end,1),tally_ver(n_liver+1:end,3));
% set(h,'MarkerFaceColor','b'); 
%%
time.total=toc;
%% grabo la estructura paciente
%if flipz==1;PET=PET(:,:,end:-1:1);end  
if ~isempty(file_paciente);load(file_paciente);end

densidad=zeros(1,length(cell));
for i=1:length(cell) 
    densidad(i)=mat(IdMat(i),1).Densidad;
end

paciente.mode=mode;
paciente.flip=flip;
paciente.flipz=flipz; %para PET
paciente.IdMAT=IdMat'; 
paciente.densidad=densidad'; %g/cm^3
% no es  necesario electrones sum_emisividad=1
%paciente.sum_emisividad=sum_emisividad;
paciente.cell=cell; 
%paciente.tally_ver=tally_ver;
paciente.corteN=corteN;
paciente.time=time;
paciente.tmesh=tmesh;
paciente.index=index;
paciente.mcnp=1; 
paciente.date=datetime("today");


%file=[directorio,'/paciente.mat'];
delete(file_paciente)
save(file_paciente,'paciente')

disp(' ')
disp('Se genero un archivo "paciente.mat" en el directorio: ')
disp(file_paciente)

