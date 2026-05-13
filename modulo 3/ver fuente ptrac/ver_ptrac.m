clc
close all
clear 

%% Version 2.1 22/11/18 
%importar datos
% o cargar datos
%% Agregar que se pueda ver la superponer la el higado y el tumor  
%%
nfig=1;
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
%% 

% 
% [p,file_paciente]=f_cargo_mat;
% if ~isempty(p)
%     paciente=p.paciente;
%     clear p archivo
%     % Ojo que Uso I para el fantoma
%       
%     if isfield(paciente,'registro')
%         if paciente.registro==1;ok(1)=1;end
%     else
%         disp(' ')
%         disp(' Las imagenes no estan registradas' )
%         return
%     end
%     if isfield(paciente,'segmentado')
%         if paciente.segmentado==1;ok(2)=1;end
%     else
%         disp(' ')
%         disp(' Las imagenes no esta segmentada' )
%         return
%     end
%     if isfield(paciente,'mcnp')
%         if paciente.mcnp==1;ok(3)=1;end
%     else
%         disp(' ')
%         disp(' No se genero el archivo MCNP' )
%         return
%     end
%     
% else
%     disp(' ')
%     disp(' Debe ingresar paciente.mat' )
%     
%     return
% end
% %%
% I=paciente.Phantom; 
% PET=paciente.PET;
% index=paciente.index; 
% index.pretumor=99; 
% vCT=paciente.vCT; 
%%
file=[];
[a,file]=f_cargo_ptract(file);

a(1,:)=[];

max=size(a,1)/3;  
%numero de visulizaciones <10000
n=500; 

if max>=1e5;max=100000;end 
max=uint32(max);

a2=zeros(max,8);
n1=1;
for i=1:3:max*3  
    a1=a(i,:);
    a2(n1,:)=a1(1,1:8);
    a1=[];
    n1=n1+1;
end
% 
pos=a2(:,1:3);

vec=a2(:,4:6); 

E=a2(:,7);

wgt=a2(:,8);
% %% isosurface
% figure(nfig)
% nfig=nfig+1; 
% set(gcf,'Render','OpenGL')
% [xr, yr, zr, imr] = reducevolume(I, [2 2 1]);
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
% % %%
% corteN=100; 
% ind=find(PET>=corteN); 
% 
% [x,y,z]=ind2sub(size(PET),ind); 
% 
% set(gcf,'NextPlot','add')
% for i=1:length(x)
%     scatter3(x(i),y(i),z(i));
%     pause(0.1)
% end 
%%
figure(nfig)
nfig=nfig+1; 
set(gcf,'NextPlot','add')
h=scatter3([pos(:,1);pos(:,1)],[pos(:,2);pos(:,2)],[pos(:,3);pos(:,3)]);
xlabel('X')
ylabel('Y')
zlabel('Z')
set(h,'Marker','.')

%figure(nfig)
%nfig=nfig+1; 
% tic 
% for i=1:n
%     x=pos(i,1);
%     y=pos(i,2);
%     z=pos(i,3);
%     x0=pos(i,1);
%     y0=pos(i,2);
%     z0=pos(i,3);
%     h=scatter3([x0;x],[y0;y],[z0,z]);
%     xlabel('X')
%     ylabel('Y')
%     zlabel('Z')
%     hold on 
%     c=rand(1,3);
%     set(h,'MarkerEdgeColor',c) 
%     set(h,'SizeData',22)
%     set(h,'MarkerFaceColor',c)
%     pause(0.01)
% end
% time1=toc;

x0=0; 
y0=0; 
z0=0; 

x=1;
y=0;
z=0; 

figure(nfig)
nfig=nfig+1;
%grafico de verificacion 
plot3([x0;x],[y0;y],[z0,z]);
xlabel('X')
hold on 
x=0;
y=1;
z=0;
h=plot3([x0;x],[y0;y],[z0,z]);
set(h,'color','g') 
ylabel('Y')
x=0;
y=0;
z=1;
h=plot3([x0;x],[y0;y],[z0,z]);
set(h,'color','r') 
xlabel('X')
ylabel('Y')
zlabel('Z')

%grafico la fuente 
tic 
figure(nfig)
nfig=nfig+1; 
for i=1:n
    x0=pos(i,1);
    y0=pos(i,2);
    z0=pos(i,3);
    %x0=0;
    %y0=0;
    %z0=0;
    % revisar
    x=x0+vec(i,1);
    y=y0+vec(i,2);
    z=z0+vec(i,3);
    h=plot3([x0;x],[y0;y],[z0;z]);
    c=rand(1,3);
    set(h,'color',c) 
    hold on 
    h=scatter3([x;x],[y;y],[z,z]);
    set(h,'MarkerEdgeColor',c) 
    set(h,'SizeData',22)
    set(h,'MarkerFaceColor',c)
    xlabel('X')
    ylabel('Y')
    zlabel('Z')
    pause(0.01)
end
time2=toc;

figure(nfig)
nfig=nfig+1;
histogram(E,100)
h=title(' Espectro de energia particulas');
set(h,'FontWeight','bold')

b3=zeros(max,8);
cell=zeros(max,1);
n1=1;
for i=3:3:max*3 
    b1=a(i,:);
    cell(n1,:)=b1(1,4);
    b1=[];
    n1=n1+1;
end

figure(nfig)
nfig=nfig+1;
histogram(cell,110)
h=title(' Distribucion de celdas  ');
set(h,'FontWeight','bold')


a3=unique(cell); 
color(1)='b'; 
color(2)='r'; 
color(3)='c'; 
color(4)='k';
color(5)='g'; 

figure(nfig)
nfig=nfig+1;
for i=1:length(a3)
    ind=cell==a3(i); 
    h=scatter3([pos(ind,1);pos(ind,1)],[pos(ind,2);pos(ind,2)],[pos(ind,3);pos(ind,3)]);
    hold on 
    set(h,'Marker','.')
    set(h,'MarkerEdgeColor',color(i));    
end    
xlabel('X')
ylabel('Y')
zlabel('Z')

%% 


