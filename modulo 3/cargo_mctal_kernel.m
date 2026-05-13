%%
% En el caso de MIRD no usar pretumor 
%Especial para Y-90
%I=Phantom;
%
% agregar micro dosimetria
% agregar en el reporte los parametros radiobiologicos
% buscar parametros radiobiologicos de tumor
% OJO el tamaño del higado
% que parametros radiobiologicos le pongo al pretumor y como lo considero
% esta considerando 10 divisiones para la curva de isodosis

%%
clc
clear 
close all
%%
% Si el error es del 100% entonces que hacer con la dosis
%%
%% Tallies
%op_tally=1;busco='tally    1  '; %mesh tally 1 igual f6
%op_tally=4;busco='tally    8  '; %tally *f8
%op_tally=2;busco='tally    3  ';
%op_tally=3;busco='tally   18 ';
%op_tally=5;busco='tally   26 ';
%op_tally=6;busco='tally    6 ';
% D1 es el tally 1
% D3 es el tally 3
%%
nfig=1;
nshow=[];
MeV2J=1.6e-13;
Bq_us=50; %esferas de resina
%op_fuente=2;
%sum_emisividad=1;
tmesh=[1,0]; %para leer el tmesh tmesh(1)=1 tipo 1 // tmesh(2)=2 tipo 3
error_eliminar=0.5; % si es mayor a uno no saco nada
version='3.10 MIRD';
Actividad_ref=3; %3 GBq
Actividad=1; % 1Bq
%% preferencias de las ventanas
% hacer funcion
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
%%
%directorio=f_creo_directorio;
%% cargo el archivo paciente con todos los datos
[p,file_paciente,directorio]=f_cargo_mat;
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
        disp(' La imagene no esta segmentada' )
        return
    end
    if isfield(paciente,'mcnp')
        if paciente.mcnp==1;ok(3)=1;end
    else
        disp(' ')
        disp(' No se genero el archivo MCNP' )
        %return
    end

else
    disp(' ')
    disp(' Debe ingresar paciente.mat' )

    return
end
%% Datos de paciente
flip=paciente.flip;
mode=paciente.mode;
vCT=paciente.vCT/10; % paso de mm a cm
%vPET=paciente.vPET/10;
densidad=paciente.densidad;
IdMAT=paciente.IdMAT;
cell=paciente.cell;
%tally_ver=paciente.tally_ver;
Phantom=paciente.Phantom;
%PET=paciente.PET;
%CT=paciente.CT;
%info_PET=paciente.info_PET;
index=paciente.index;
corteN=paciente.corteN;
PatientID=paciente.PatientID;
UnitsPET=paciente.UnitsPET;
% Actividad=paciente.Actividad;
if isfield(paciente,'file_mcnp')
    file_mcnp=paciente.file_mcnp;
else
    file_mcnp=[];
end
time=paciente.time;
%% OJO por ahora uno solo
index.pretumor=99;
%% size
if isfield(paciente,'recorte')
    recorte=paciente.recorte;
else
    recorte=[];
end
if ~isempty(recorte)
    %recorte=[ymin ymax xmin xmax]
    I1=Phantom(recorte(1):recorte(2),recorte(3):recorte(4),:);
    PET1=PET(recorte(1):recorte(2),recorte(3):recorte(4),:);
    CT1=CT(recorte(1):recorte(2),recorte(3):recorte(4),:);
else
    I1=Phantom;
%    PET1=PET;
%    CT1=CT;
end
%clear PET CT I paciente recorte
%%
% IND=PET1<=corteN;
% PET1(IND)=0;
%%
s=size(I1);
if isempty(nshow);nshow=s(3);end
%%
% if strcmp(UnitsPET, 'BQML')
%    v_voxel=prod(vPET);
%    PET1=PET1.*v_voxel;
%    UnitsPET='Bq';
%    clear v_voxel
% end
%if strcmp(UnitsPET, 'Bq')  65027
%PET1=double(PET1);
%Actividad=sum(PET1(:));


A_GBq=Actividad/1e9;

IND_liver=I1==index.liver; 
IND_tumor=I1==index.tumor; 

PET1(IND_liver)=0.25*Actividad/1e5; 
PET1(IND_tumor)=0.75*Actividad/1e5; 


uS=PET1./Bq_us; %numero de uS
uS_max=max(uS(:));
uS_promedio=mean(uS(:));
uS_total=sum(uS(:));

clear A A1 A2 IND IND2 IND3
% %%
% figure(nfig)
% nfig=nfig+1;
% set(gcf,'Render','OpenGL')
% ax1=axes;
% ax2=axes;
% %nfig=nfig+1;
% max1=max(uS(:));
% gray=colormap(gray);
% jet=colormap(jet);
% %for nslice=1:nshow
% for nslice=1:nshow
%     imshow(I1(:,:,nslice),[],'parent',ax1,'colormap',gray);
%     freezeColors;
%     %hold on
%     imshow(uS(:,:,nslice),[],'parent',ax2,'colormap',jet) ;
%     %colormap(jet(16))
%     %colormap(jet)
%     caxis([0 max1])
%     colorbar
%     alpha 0.4
%     P=get(ax2,'Position');
%     set(ax1,'Position',P);
%     h=title([' Fusion CT-uS slice: # ',num2str(nslice)]);
%     set(h,'FontWeight','bold')
%     pause(0.01)
% end
% 
% %% Agrego el pretumor
% %I1=f_pretumor(I1,index);
% %cell(end+1)=index.pretumor;
% %%
% f_HDV_Actividad(uS,I1,index.liver,nfig)
% set(gca,'NextPlot','add')
% %f_HDV_Actividad(uS,I1,index.pretumor,nfig)
% f_HDV_Actividad(uS,I1,index.tumor,nfig)
% 
% h_title=title(['Cumulative uSphere Volume Histogram, uSphere: ',num2str(uS_total,'%7.2e')]);
% set(h_title,'FontWeight','bold')
% nfig=nfig+1;
% %% MIRD
% %organo=90; %liver
% %organo=100; %tumor
% 
% [T_N,volumen_liver,volumen_tumor] = f_T_N(PET1,Phantom,vCT);
% 
% densidad_liver=1.06; %g/cm^3
% 
% m_liver=volumen_liver*densidad_liver;
% m_liver=m_liver/1000; %kg
% m_tumor=volumen_tumor*densidad_liver;
% m_tumor=m_tumor/1000;
% 
% k=48.98; % constante J-s
% SF=0; % dado que
% FU_normal=(1-SF)*(volumen_liver/(T_N*volumen_tumor+volumen_liver));
% FU_tumor=(1-SF)*(T_N*volumen_tumor/(T_N*volumen_tumor+volumen_liver));
% 
% %Actividad_GBq=D_tumor*m_tumor/(k*FU_tumor);
% D_liver_Gy=A_GBq*k*FU_normal/m_liver;
% D_tumor_Gy=A_GBq*k*FU_tumor/m_tumor;
% %%
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
% % pretumor
% p=patch(isosurface(xr,yr,zr,imr,index.pretumor));
% isonormals(xr,yr,zr,imr,p);
% 
% transparency=0.5;
% set(p,'EdgeColor','none');
% set(p,'FaceColor','y');
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
% lighting phong ;
% 
% %%
% %RBE=1;
% %% buscar bien los de tumor
% p_radiobiologicos.liver.alfa_beta=2.5; % alfa/beta Gy
% p_radiobiologicos.liver.alfa=0.0104;   %Gy^-1; Chiesa TD50=41.6
% p_radiobiologicos.liver.mu=0.28; % h^-1 T=2.5 h
% p_radiobiologicos.tumor.alfa_beta=10;
% p_radiobiologicos.tumor.alfa=0.0104;
% p_radiobiologicos.tumor.mu=0.28;
 T=64.1;%h ICRP 107
 lamda=log(2)/T; % h
 T=T*3600; % seg
 lamda1=log(2)/T;  %seg
 t=1/lamda1; % tiempo de integracion 0 a Inf
% % para el caso de e- sum_emisividad=1;
% %%
% % No pregunto actividad ni shunt dado que esta cuentificado en Bq
% % Haq chequear muy bien
% clc
% disp(' ')
% %Actividad =input(' Ingrese la Actividad [GBq]:   ');
% disp(' ')
% %shunt=input(' Ingrese el shunt pulmonar [%]:    ');
% clc
% disp(' ')
% disp('  ')
% disp([' N de desintegraciones por unidad de actividad: ',num2str(t)])
% disp(' ')
% disp(' Se cargaron los parametros radiobiologicos para Higado: ')
% disp('  ')
% disp([' lamda [h]: ',num2str(lamda)])
% disp([' u [h]: ',num2str(p_radiobiologicos.liver.mu)])
% disp([' alfa/beta [Gy]: ',num2str(p_radiobiologicos.liver.alfa_beta)])
% disp([' alfa [Gy^-1]: ',num2str(p_radiobiologicos.liver.alfa)])
% disp('  ')
% disp('  PRESIONE CUALQUIER TECLA PARA CONTINUAR')
% pause(0.8)
% clear T lamda1
%% calculo la densidad y la masa
%Actividad=A; % Bq
volumen=prod(vCT); %cm^3
masa=densidad.*volumen; % g
masa=masa./1000;   %kg
densidad=densidad./1000; %kq/cm^3
%% flipeo el phantoma
%I1=f_flip(I1,flip);
%% cargo el acrivo MCTALL
%% tally 1
%% agreagar que se carge el mctall aca
if ~isempty(file_mcnp)
    clc
    disp('  ')
    disp(file_mcnp)
    disp('  ')
    res=input(' Desea usar ese archivo mctall   (NO=0) // (SI~=0):  ');
    if res==0;file_mcnp=[];clc;end
    clear resp
else
    file_mcnp=f_file_mctall;
end

clc
%%
%% tally 1
if tmesh(1)==1
    op=1;     % tally 1
    tic
    [D1,error1,file_mcnp]=f_cargo_mctall(s,op,file_mcnp);
    time_lectura_tally=toc;
    % Dosis MeV/cm^3/source_particle
    % flip
    D1=f_flip(D1,flip);
    error1=f_flip(error1,flip);
    %error1=error1.*100;

end
% tally 3
%usar parfor
if tmesh(2)==1
    op=2; % tally 3
    tic
    [D3,error3,file_m]=f_cargo_mctall(s,op,file_mcnp);
    time_lectura_tally=toc;
    % Dosis MeV/cm^3/source_particle
    % flip
    D3=f_flip(D3,flip);
    error3=f_flip(error3,flip);
    %error3=error3;
end
%%
%Dosis MeV/cm^3/source_particle
%Gy-Eq/source_particle meshtally 1-3
if tmesh(1)==1
    D3=D1;
    error3=error1;
    %D1org=D1;
    clear D1 error1
end
%% elimino error
%D3=smooth3(D3);
%IND=error3>=error_eliminar;
%D3(IND)=0;
%% puede haber negativo poca estadistica
% IND=D3<0;
% D3(IND)=0;
% %% saco dosis en aire
% IND=I1==index.aire;
% D3(IND)=0;
%%
%I1=f_flip(I1,flip);
%PET1=f_flip(PET1,flip);
%cell(end+1)=index.pretumor;
%densidad(end+1)=densidad(5); %higado
%% 
Kernel=D3; %MeV/cm3 
Actividad=1e9;  % GBq
densidad=1.09; 
V=volumen; 
masa=densidad*V; 
masa=masa./1000; 

a=1.498e-13*t*Actividad; % recupero los 49.98 del pag 112 
max1=max(Kernel(:))*V;
max2=max1*MeV2J;
b=max2*t*Actividad; 

sum1=sum(Kernel(:)*V);
sum2=sum1*MeV2J; 

c=sum2*t*Actividad; % tengo lo 50 Gy 



Kernel=Kernel.*V; 
Kernel=Kernel.*MeV2J; 
Kernel=Kernel*t; 
Kernel=Kernel.*Actividad; 
Kernel=Kernel./masa;

% la actividad dede estar en GBq

maxK=max(Kernel(:));
minK=min(Kernel(:));

figure(nfig)
nfig=nfig+1;
%Kernel=D3;
a=Kernel(:,:,25);
transparencia=1;
alphaMask = zeros(size(a));
alphaMask(a > 0) = transparencia;
h = imshow(a,[]);
%set(app.axes_PET, 'Color', 'none');
set(h, 'AlphaData', alphaMask);
clear jet 
colormap(jet(5000))
colorbar



% %%
% 
% D3=f_div_densidad(D3,I1,cell,densidad); %MeV/kg
% 
% D3=D3.*MeV2J; %J/kg=Gy
% 
% %D3=D3.*t.*Actividad.*sum_emisividad.*RBE.*(1-shunt/100);
% % la actividad es absoluta
% D3=D3.*t.*Actividad;
%%
%Kernel=D3; 
%%
% max3=max(D3(:));
% min3=min(D3(:));
% %
% figure(nfig)
% nfig=nfig+1;
% set(gcf,'Render','OpenGL')
% ax1=axes;
% ax2=axes;
% %nfig=nfig+1;
% max1=max(error3(:));
% gray=colormap(gray);
% jet=colormap(jet);
% for nslice=1:nshow
%     imshow(I1(:,:,nslice),[],'parent',ax1,'colormap',gray);
%     %colormap(gray)
%     %freezeColors;
%     %hold on
%     imshow(error3(:,:,nslice),[],'parent',ax2,'colormap',jet) ;
%     %colormap(jet(16))
%     %colormap(jet)
%     clim([0 max1])
%     colorbar
%     alpha 0.4
%     P=get(ax2,'Position');
%     set(ax1,'Position',P);
%     h=title([' Fusion CT-error # ',num2str(nslice)]);
%     set(h,'FontWeight','bold')
%     pause(0.1)
% end
% %%
% figure(nfig)
% nfig=nfig+1;
% set(gcf,'Render','OpenGL')
% ax1=axes;
% ax2=axes;
% %nfig=nfig+1;
% max1=max(D3(:));
% gray=colormap(gray);
% jet=colormap(jet);
% for nslice=1:nshow
%     imshow(I1(:,:,nslice),[],'parent',ax1,'colormap',gray);
%     %colormap(gray)
%     %freezeColors;
%     %hold on
%     imshow(D3(:,:,nslice),[],'parent',ax2,'colormap',jet) ;
%     %colormap(jet(16))
%     %colormap(jet)
%     clim([0 max1])
%     colorbar
%     alpha 0.4
%     P=get(ax2,'Position');
%     set(ax1,'Position',P);
%     h=title([' Fusion CT-Dosis # ',num2str(nslice)]);
%     set(h,'FontWeight','bold')
%     pause(0.1)
% end
%%
%organo=index.liver;
%tumor=index.tumor;
%%
% los parametros radiologicos de higado y tumor son iguales
% cargar el index directamante

%BED3=f_BED(D3,I1,p_radiobiologicos,lamda,index,cell); %Gy BED
%% Micro estructuras
%Esto es valido solo para el higado
%por lo tanto hay que usar el Phantoma para seleccionar solo el higado
%masa1=1.06*prod(vPET);

% 
% % % agregar que tabla es NO
%micro.hepatic_arteria=154; %Gy*g*MBq^-1;
%micro.bile_duct=85;
%micro.portal_vein=85;
%micro.parenquima=50;
%micro.central_vein=45;

%A=PET1.*1e-6; %Bq2MBq
%A=A./masa1; %Bq/g

% tengo que consideras solo el higado
%ind=I1==index.liver;

% Dosis.liver.hepatic_arteria=A(ind).*micro.hepatic_arteria;        %Bq/g*(Gy*g*Bq^-1)=Gy
% Dosis.liver.max_hepatic_Arteria=max(Dosis.liver.hepatic_arteria(:));
% Dosis.liver.bile_duct=A(ind).*micro.bile_duct;        %Bq/g*(Gy*g*Bq^-1)=Gy
% Dosis.liver.max_bile_duct=max(Dosis.liver.bile_duct(:));
% Dosis.liver.portal_vein=A(ind).*micro.portal_vein;        %Bq/g*(Gy*g*Bq^-1)=Gy
% Dosis.liver.max_portal_vein=max(Dosis.liver.portal_vein(:));
% Dosis.liver.parenquima=A(ind).*micro.parenquima;        %Bq/g*(Gy*g*Bq^-1)=Gy
% Dosis.liver.max_parenquima=max(Dosis.liver.parenquima(:));
% Dosis.liver.central_vein=A(ind).*micro.central_vein;        %Bq/g*(Gy*g*Bq^-1)=Gy
% Dosis.liver.max_central_vein=max(Dosis.liver.central_vein(:));
% 
% ind=I1==index.tumor;
% Dosis.tumor.hepatic_arteria=A(ind).*micro.hepatic_arteria;        %Bq/g*(Gy*g*Bq^-1)=Gy
% Dosis.tumor.max_hepatic_Arteria=max(Dosis.tumor.hepatic_arteria(:));
% Dosis.tumor.bile_duct=A(ind).*micro.bile_duct;        %Bq/g*(Gy*g*Bq^-1)=Gy
% Dosis.tumor.max_bile_duct=max(Dosis.tumor.bile_duct(:));
% Dosis.tumor.portal_vein=A(ind).*micro.portal_vein;        %Bq/g*(Gy*g*Bq^-1)=Gy
% Dosis.tumor.max_portal_vein=max(Dosis.tumor.portal_vein(:));
% Dosis.tumor.parenquima=A(ind).*micro.parenquima;        %Bq/g*(Gy*g*Bq^-1)=Gy
% Dosis.tumor.max_parenquima=max(Dosis.tumor.parenquima(:));
% Dosis.pretumor.central_vein=A(ind).*micro.central_vein;        %Bq/g*(Gy*g*Bq^-1)=Gy
% Dosis.pretumor.max_central_vein=max(Dosis.pretumor.central_vein(:));
% % 
% % ind=I1==index.pretumor;
% % Dosis.pretumor.hepatic_arteria=A(ind).*micro.hepatic_arteria;        %Bq/g*(Gy*g*Bq^-1)=Gy
% % Dosis.pretumor.max_hepatic_Arteria=max(Dosis.tumor.hepatic_arteria(:));
% % Dosis.pretumor.bile_duct=A(ind).*micro.bile_duct;        %Bq/g*(Gy*g*Bq^-1)=Gy
% % Dosis.pretumor.max_bile_duct=max(Dosis.tumor.bile_duct(:));
% % Dosis.pretumor.portal_vein=A(ind).*micro.portal_vein;        %Bq/g*(Gy*g*Bq^-1)=Gy
% % Dosis.pretumor.max_portal_vein=max(Dosis.tumor.portal_vein(:));
% % Dosis.pretumor.parenquima=A(ind).*micro.parenquima;        %Bq/g*(Gy*g*Bq^-1)=Gy
% % Dosis.pretumor.max_parenquima=max(Dosis.tumor.parenquima(:));
% % Dosis.pretumor.central_vein=A(ind).*micro.central_vein;        %Bq/g*(Gy*g*Bq^-1)=Gy
% % Dosis.pretumor.max_central_vein=max(Dosis.pretumor.central_vein(:));



clear A masa1

% figure(nfig)
% nfig=nfig+1;
% set(gcf,'Render','OpenGL')
% ax1=axes;
% ax2=axes;
% %nfig=nfig+1;
% max1=max(D3(:));
% gray=colormap(gray);
% jet=colormap(jet);
% nslice=171;
% for nslice=1:nshow
%     imshow(I1(:,:,nslice),[],'parent',ax1,'colormap',gray);
%     %colormap(gray)
%     %freezeColors;
%     %hold on
%     imshow(D3(:,:,nslice),[],'parent',ax2,'colormap',jet) ;
%     %colormap(jet(16))
%     %colormap(jet)
%     caxis([0 max1])
%     colorbar
%     alpha 0.4
%     P=get(ax2,'Position');
%     set(ax1,'Position',P);
%     h=title([' Fusion CT-Dosis # ',num2str(nslice)]);
%     set(h,'FontWeight','bold')
%     pause(0.1)
% end
% f_mostrar_NewCallback;
%%
%% boxplot

% IND=I1==index.liver;
% %IND1=I1==index.pretumor;
% %IND2=IND+IND1;
% A=D3(IND);
% IND=I1==index.tumor;
% B=D3(IND);
% 
% figure(nfig)
% nfig=nfig+1;
% boxplot(A);
% title('Liver')
% 
% figure(nfig)
% nfig=nfig+1;
% boxplot(B);
% title('Tumor')
% clear A B IND IND1

%% Reporte

% %
% name='Reporte.txt';
% archivo=[directorio,name];
% fid=fopen(archivo, 'w+');
% status=fclose(fid);
% if status==0
%     %clcsD
%     disp('  ')
%     disp(' El archivo se creo correctamente')
% else
%     disp(' ')
%     disp(' EL ARCHIVO NO SE CREO CORRECTAMENTE')
%     return
% end
% clear status dirctorio1
% fid=f_genero_titulo(archivo,version,PatientID);
% clear version PatientID
% 
% %%
% fprintf(fid,'.................................................................. \n');
% fprintf(fid,' Actividad  =  ');
% fprintf(fid,'% g',A_GBq);
% fprintf(fid,' GBq \n');
% 
% %% DVH
% clc
% figure(nfig)
% % agregar label
% % no esta muy prolijo como se seleccionan los organos
% for i=1:numel(cell) %solo para higado sano y tumor
%     organo=cell(i);
%     %if organo>=tumor
% 
%     if organo==30;txt='Tejido Blando';end
%     if organo==50;txt='Pulmon';end
%     if organo==80;txt='Hueso';end
%     if organo==90;txt='Hígado sano';color=1;end
%     if organo>=100;txt='Tumor';color=2;end
%     if organo==99;txt='Pretumor';color=3;end
% 
%     [BEDmean,BEDmin,BEDmax,sBED] =f_mean(I1,BED3,organo);
% 
%     EUBED3=f_EUBED(I1,BED3,organo,p_radiobiologicos.liver.alfa);
% 
%     EUD3=f_EUD(I1,D3,organo,p_radiobiologicos.liver.alfa);
% 
%     [D3mean,D3min,D3max,sD] =f_mean(I1,D3,organo);
% 
%     EQD2=f_EQD2(D3mean,organo,p_radiobiologicos,index);
% 
%     volumen=f_HDV(D3,I1,organo,vCT,nfig);
% 
% 
% 
%     fprintf(fid,'.................................................................. \n');
%     fprintf(fid,'.................................................................. \n');
%     fprintf(fid,' Dosis promedio del ');
%     fprintf(fid,txt);
%     fprintf(fid,' = ');
%     fprintf(fid,'% g',D3mean);
%     fprintf(fid,' Gy \n' );
%     fprintf(fid,'.................................................................. \n');
%     fprintf(fid,' Dosis min del ');
%     fprintf(fid,txt);
%     fprintf(fid,' = ');
%     fprintf(fid,'% g',D3min);
%     fprintf(fid,' Gy \n' );
%     fprintf(fid,'.................................................................. \n');
%     fprintf(fid,' Dosis max del ');
%     fprintf(fid,txt);
%     fprintf(fid,' = ');
%     fprintf(fid,'% g',D3max);
%     fprintf(fid,' Gy \n' );
%     fprintf(fid,'.................................................................. \n');
%     fprintf(fid, ' Desviasión estandar del ');
%     fprintf(fid,txt);
%     fprintf(fid,'  = ');
%     fprintf(fid,'% g',sD);
%     fprintf(fid,' Gy \n' );
%     fprintf(fid,'.................................................................. \n');
%     fprintf(fid,' BED promedio del ');
%     fprintf(fid,txt);
%     fprintf(fid,' = ');
%     fprintf(fid,'% g',BEDmean);
%     fprintf(fid,' Gy BED \n' );
%     fprintf(fid,'.................................................................. \n');
%     fprintf(fid,' EUD del ');
%     fprintf(fid,txt);
%     fprintf(fid,' = ');
%     fprintf(fid,'% g',EUD3);
%     fprintf(fid,' Gy \n' );
%     fprintf(fid,'.................................................................. \n');
%     fprintf(fid,' EUBED del ');
%     fprintf(fid,txt);
%     fprintf(fid,' = ');
%     fprintf(fid,'% g',EUBED3);
%     fprintf(fid,' Gy BED \n' );
%     fprintf(fid,'.................................................................. \n');
%     fprintf(fid,' EQD2 del ');
%     fprintf(fid,txt);
%     fprintf(fid,' = ');
%     fprintf(fid,'% g',EQD2);
%     fprintf(fid,' Gy \n' );
%     fprintf(fid,'.................................................................. \n');
%     if organo==90
%         %fprintf(fid,'.................................................................. \n');
%         fprintf(fid,' Dosis MIRD del ');
%         fprintf(fid,txt);
%         fprintf(fid,' = ');
%         fprintf(fid,'% g',D_liver_Gy);
%         fprintf(fid,' Gy \n' );
%     end
%     if organo==100
%         %fprintf(fid,'.................................................................. \n');
%         fprintf(fid,' Dosis MIRD del ');
%         fprintf(fid,txt);
%         fprintf(fid,' = ');
%         fprintf(fid,'% g',D_tumor_Gy);
%         fprintf(fid,' Gy \n' );
%     end
%     fprintf(fid,'.................................................................. \n');
%     fprintf(fid,' Volumen del ');
%     fprintf(fid,txt);
%     fprintf(fid,' = ');
%     fprintf(fid,'% g',volumen);
%     fprintf(fid,' cm^3 \n' );
% 
%     if organo==90
%         Dosis.liver.min=D3min;
%         Dosis.liver.max=D3max;
%         Dosis.liver.mean=D3mean;
%         Dosis.liver.BED=BEDmean;
%         Dosis.liver.EUD=EUD3;
%         Dosis.liver.MIRD=D_liver_Gy;
%         Dosis.liver.EQD2=EQD2;
%     end
%     if organo==100
%         Dosis.tumor.min=D3min;
%         Dosis.tumor.max=D3max;
%         Dosis.tumor.mean=D3mean;
%         Dosis.tumor.BED=BEDmean;
%         Dosis.tumor.EUD=EUD3;
%         Dosis.tumor.MIRD=D_tumor_Gy;
%         Dosis.tumor.EQD2=EQD2;
%     end
%     if organo==99
%         Dosis.pretumor.min=D3min;
%         Dosis.pretumor.max=D3max;
%         Dosis.pretumor.mean=D3mean;
%         Dosis.pretumor.BED=BEDmean;
%         Dosis.pretumor.EUD=EUD3;
%         %Dosis.pretumor.MIRD=D_tumor_Gy;
%     end
% 
% 
% 
% end
% nfig=nfig+1;
% fclose(fid);
% 
% % %% isodosis
% % maximo=max(D3(:));
% % %ind=D3==maximo;
% % %[x,y,z]=ind2sub(size(D3),ind);
% % D31=floor(D3.*100./maximo);
% % D3=smooth3(D3);
% %
% % figure(1000)
% % patch(isocaps(D3,.5),...
% %    'FaceColor','interp','EdgeColor','none');
% % p1 = patch(isosurface(D3,.5),...
% %    'FaceColor','none','EdgeColor','none');
% % isonormals(D3,p1);
% % view(3);
% % axis vis3d tight
% % camlight left
% % colormap('jet');
% % lighting gouraud
%% 



%%

% Dosis.voxel=D3;
% 
% D31=smooth3(D3);
% maximo=max(D3(:));
% minimo=min(D3(:));
% ind=find(maximo==D3);
% [x,y,z]=ind2sub(size(D3),ind);
% 
% D31=floor(D31.*100./maximo);
% v=10:10:100;  % esta definido en 10 parar la dividir la dosis se podria variar 
% 
% ncolor=10;
% %ncolor=ncolor-1; 
% map=colormap(jet);
% s=length(map);
% a=round(s(1)/(ncolor-1));
% map=map(1:a:s(1),:);
% colormap(map);
% 
% A=D31(:,:,z)'; % lo veo sobre una imagen
% A=imrotate(A,90);
% figure(nfig)
% nfig=nfig+1;
% ax1=axes;
% set(gcf,'Render','OpenGL')
% imshow(Phantom(:,:,z),[],'Parent',ax1)
% colormap(gray)
% freezeColors
% set(ax1,'NextPlot','add')
% ax2=axes;
% [C,h]=contour(ax2,A,v);
% colormap(map);
% set(ax2,'DataAspectRatio',[1,1,1])
% set(ax2,'Visible','off')
% set(ax2,'CLim',[10,100])
% set(h,'Fill','off')
% set(h,'LineWidth',1)
% h=title(ax1,[' Fusion CT-isoDosis slice: # ',num2str(z)]);
% set(h,'FontWeight','bold')
% 
% 
% a=(maximo-minimo)/(ncolor-1);
% c=(minimo:a:maximo);
% 
% n=length(c);
% c1{n,1}=0; 
% for i=1:n
%     a1=c(:,i);
%     txt=sprintf('%0.0f',a1);
%     c1{i,1}=[txt,'  Gy'];
% end
% 
% h_colorbar=colorbar;
% set(h_colorbar,'Position',[0.85 0.11 0.05 0.81]);
% set(h_colorbar,'FontWeight','bold');
% cmfit(map)
% set(h_colorbar,'TickLabels',c1);
% 
% dcm_obj = datacursormode(nfig-1);
% set(dcm_obj,'UpdateFcn',{@myupdatefcn,Dosis})

%
% function test_main
% % Plots graph and sets up a custom data tip update function
% fig = figure('DeleteFcn','doc datacursormode');
% X = 0:60;
% t = (X)*0.02;
% Y = sin(-16*t);
% plot(X,Y)
% dcm_obj = datacursormode(fig);
% set(dcm_obj,'UpdateFcn',{@myupdatefcn,t})
%
% function txt = myupdatefcn(~,event_obj,t)
% % Customizes text of data tips
% pos = get(event_obj,'Position');
% I = get(event_obj, 'DataIndex');
% txt = {['X: ',num2str(pos(1))],...
%        ['Y: ',num2str(pos(2))],...
%        ['I: ',num2str(I)],...
%        ['T: ',num2str(t(I))]};

%%

% figure(nfig)
% nfig=nfig+1;
%  set(gcf,'Render','OpenGL')
%  for i=1:nshow
%      if i~=1
%          cla(ax1)
%          cla(ax2)
%      end
%       A=D31(:,:,i)'; % lo veo sobre una imagen
%       A=imrotate(A,90);
%       ax1=axes;
%       imshow(Phantom(:,:,i),[],'Parent',ax1)
%       colormap(gray)
%       freezeColors
%       set(ax1,'NextPlot','add')
%       ax2=axes;
%       [C,h]=contour(ax2,A,v);
%       colormap(map)
%       set(ax2,'DataAspectRatio',[1,1,1])
%       set(ax2,'Visible','off')
%       set(ax2,'CLim',[10,100])
%       set(h,'Fill','off')
%       set(h,'LineWidth',1)
%       set(h,'Fill','on')
%       set(h,'ShowText','off')
%       alpha(0.4)
%       h_colorbar=colorbar;
%       set(h_colorbar,'Position',[0.85 0.11 0.05 0.81]);
%       set(h_colorbar,'FontWeight','bold');
%       %set(h_colorbar,'Color',cm)
%       cmfit(map);
%       set(h_colorbar,'TickLabels',c1);
%       h_tittle=title(ax1,[' Fusion CT-isoDosis slice: # ',num2str(i)]);
%       pause(0.01)
%       if i~=nshow
%           delete(h_colorbar)
%           delete(h_tittle)
%       end
%  end
%  clear A D31

%%
% time.lectura_tally=time_lectura_tally;
% clear time_lectura_tally
% %% guardo paciente
% if ~isempty(file_paciente);load(file_paciente);end
% 
% %paciente.p_radiobiologicos=p_radiobiologicos;
% paciente.lamda=lamda;
% paciente.file_mcnp=file_mcnp;
% paciente.Actividad_GBq=A_GBq;
% paciente.t_integracion=t;
% paciente.date_evaluation=datetime('today');
% paciente.time=time;
% paciente.error_eliminar=error_eliminar;
% paciente.Dosis=Dosis;
% %paciente.BED=BED3;
% paciente.tmesh=tmesh;
% %paciente.micro=micro;
% paciente.index=index; % se agrega el pretumor
% paciente.Phantom=I1;
% %paciente.UnitsPET=UnitsPET;
% %% save paciente
% 
% delete(file_paciente);
% save(file_paciente,'paciente');

file_kernel=[directorio,'/kernel.mat'];
save(file_kernel,'Kernel');

disp(' ')
disp('....................................................................')
disp('....................................................................')
disp('    Se genero el archivo "paciente.mat" y "Repote.txt" en el directorio : ')
disp(' ')
disp(directorio)









