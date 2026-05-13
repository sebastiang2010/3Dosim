close all
%figure(1000)

% I=zeros(size(Phantom)); 
% I(Phantom==2)=1;
% %D1=zeros(size(Phantom));
D1=D;
ind=Phantom==2;
D1(~ind)=0;

BW_fill=zeros(size(Phantom));
BW=zeros(size(Phantom));
for i=1:size(Phantom,3)
[level,em] = graythresh(Phantom(:,:,i));
BW(:,:,i) = im2bw(Phantom(:,:,i),level);
BW_fill(:,:,i)=imfill(BW(:,:,i),'holes');
end
BW_fill(ind)=2;

% value_skin=10;
% Phantom(ind)=value_skin;
% ind=Phantom==3;
% Phantom(ind)=9;

D=D1;
clear D1


I=squeeze(BW_fill);%%%paso de 4-D a 3-D
%[xr, yr, zr, imr] = reducevolume(I, [2 2 1]);
[xr, yr, zr, imr] = reducevolume(I, [1 1 1]); 

%maximo=max(D(:));
%ind=find(D==maximo);
%[x,y,z]=ind2sub(s_o,ind);
%D=floor(D.*100./maximo);
%D1=round(D(:,:,z)*100/maximo);%


%imr=smooth3(imr,'gaussian');
imr=smooth3(imr);
%a=max(imr(:));
% a=0.3333;
% imr(imr==a)=10;

figure(500)
imshow(imr(:,:,3),[])

%D=reducevolume(D, [2 2 1]);
D=reducevolume(D, [1 1 1]); 

%ver si se puede hacer con una binaria
value_skin=1;
%p=patch(isosurface(xr,yr,zr,imr,value_skin,D));
fvc=isosurface(xr,yr,zr,imr,value_skin,D);
figure(1000)
set(gcf,'Render','OpenGL')
%fvc=isosurface(imr,value_skin,D);
p=patch('Faces',fvc.faces,'Vertices',fvc.vertices,'FaceVertexCData',fvc.facevertexcdata);



maximo=max(D(:));
minimo=min(D(:));
max1=max(fvc.facevertexcdata); %%maximo local 
min1=min(fvc.facevertexcdata); %%minimo local 

isonormals(xr,yr,zr,imr,p);
%set(p,'Tag','3D');

% data_obj.Tag=5; 
% data_obj.Dosis=D; 
% transparency=get(handles.alfa_p,'Value');
transparency=1; 
% clear D1 D

shading interp
set(p,'EdgeColor','none');
set(p,'FaceColor','interp');
%set(p,'CDataMapping','scaled');
%set(p,'UserData',data_obj);
set(p,'FaceAlpha',transparency); 

%% colorbar modificicar para que se vea 10 20 30 40 50 60 100 
freezeColors;

% a=(maximo-minimo)/10;
% c=(minimo:a:maximo);
%a=(max1-min1)/10;%no redondear
div=10;
a=(max1-min1)/div;%no redondear
c=min1:a:max1;

nmap=max1; 
map=jet(nmap);
a=round(nmap/div);
map=map(1:a:nmap,:);
colormap(map);

n=length(c);
for i=1:n
    a1=[];
    a1=c(:,i);
    txt=sprintf('%0.2f',a1);
    c1{i,1}=[txt,'  Gy-Eq'];
end

h_colorbar=colorbar;
set(h_colorbar,'position',[0.8 0.11 0.05 0.8]);
set(h_colorbar,'ytick',c);
set(h_colorbar,'yticklabel',c1);
set(h_colorbar,'ylim',[min1 max1+0.04]);
set(h_colorbar,'FontWeight','bold');
set(h_colorbar,'YGrid','on');

% hay que sacarlo de paciente
x=1/dx;
y=1/dy;
%z=dz;
z=1/0.25; 
%z=z*3;
%daspect('auto') 
daspect([x y z]) 
%view(az,el);

camlight; 
lighting phong ;

% set(handles.alfa_p,'UserData',p);
% set(handles.dosis_tumour,'BackGroundColor',[0.502  1  0]);
% color_gris=get(handles.images,'Color');
% set(handles.dosis_skin,'BackGroundColor',color_gris);
% set(handles.isosurface2,'BackGroundColor',color_gris);
% set(figs,'Pointer','arrow');

% fig=findobj('-regexp','Tag','figura_mensaje');
% delete(fig);
% fig=findobj('-regexp','Tag','figura_mensaje');
% delete(fig);

%handles.input.h_colorbar=h_colorbar;
% guidata(hObject, handles);
% 
 datacursormode on;
% f_doc_datacursormode;



%revisar del sphere
% [x, y] = getpts(gcf);
% x1=round(x(1));
% y1=round(y(1));
% disp(' ')
% disp(' ')
% disp(['Punto  x:',num2str(x1),' y:',num2str(y1)]);
% disp(' ');
% disp(['Dosis [Gy-Eq]: ',num2str(D(x1,y1,z))]);




