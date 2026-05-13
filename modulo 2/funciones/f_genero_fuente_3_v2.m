function f_genero_fuente_3_v2(archivo,tvoxel,cell,I,A,fuentes,corteN) 

op_puntual=2;
%n_prueba=1000;
% version 2.1 % 08/03/18
tvoxel=quant(tvoxel,0.001); 
tvoxel=tvoxel./10; % de mm a cm 
%corteN=100; % numero de cunetas en las que corto la probabilidad 

% I es el PHANTOMA 
% A es el SPECT %hay que verificar que la fuente este normalizada
%%
idfuente=1; % una que esta cargada
%%
fid=fopen(archivo, 'a+'); %agregar datos al archivo
%% aca va el ingreso de la fuente 
nslice=size(I,3);
a=size(I,1);
b=size(I,2);
%% sacar la fuente que quedo en aire index=1;
%I y SPECT=A tienen que ser iguales
ind=I==1;
A(ind)=0;
%%
%%
E=fuentes(idfuente,1).E;
Y=fuentes(idfuente,1).Yield;
Nombre=fuentes(idfuente,1).Nombre;
%par=fuentes(idfuente,1).par; %particula

%if par==3;sum_emisividad=1;else sum_emisividad=sum(Y(:));end
tvoxel=quant(tvoxel,0.001);
% clc
% parar=1;
% while parar==1
%     disp('  ')
%     disp('  ')
%     op_puntual=input(' Fuente puntual centro del voxel [1] // Fuente uniformemente distribuida voxel [2]: ');
%     a2=[1,2];
%     a1=op_puntual==a2(1:end);
%     if sum(a1)==1
%         parar=-1;
%     else
%         clc
%         disp('  ');
%         disp(' La opcion no es correcta');
%     end
% end
% clear parar a1 a2



fprintf(fid,'c FUENTE \n');
if op_puntual==1
    fprintf(fid,'sdef erg d1 x %g',tvoxel(1)/2); %la posicion de la fuente en el centro del voxel
    fprintf(fid,' y %g',tvoxel(2)/2);
    fprintf(fid,' z %g',tvoxel(3)/2);
    fprintf(fid,' cell d5 par e ');
    fprintf(fid,'\n');
else
    fprintf(fid,'sdef erg d1 x d2 y d3 z d4 cell d5  par e \n');% la
    fprintf(fid,'c Fuente de ');
    fprintf(fid,Nombre);
    fprintf(fid,'\n');
end
% if par==2;
%     fprintf(fid,'c Sum emisividad :%g \n',sum_emisividad);
%     fprintf(fid,'c Distribucion discreta \n');
%     fprintf(fid,'#    si1   sp1 \n');
%     fprintf(fid,'      L         D    \n');
%     figure(100)
%     bar(E,Y);
%     set(gca,'XLim',[0 max(E)+1]);
%     h=xlabel('Energia [MeV]');
%     set(h,'FontWeight','bold');
%     h=ylabel('P(E)');
%     set(h,'FontWeight','bold');
%     pause(2)
%     close(gcf)
% elseif par==3;
fprintf(fid,'c Espectro normalizado a una transicion nuclear [Bq s] \n');
fprintf(fid,'c Distribucion continua \n');
fprintf(fid,'#    si1   sp1 \n');
fprintf(fid,'       A           D   \n');
fprintf(fid,'      -1           0  \n');
figure(100);
plot(E,Y);
%set(gca,'XLim',[0 max(E)]);
h=xlabel('Energia [MeV]');
set(h,'FontWeight','bold');
h=ylabel('P(E)/desintegracion' );
set(h,'FontWeight','bold');
pause(2)
close(gcf)
%end
for i=1:length(E)
    fprintf(fid,'       %e',E(i));
    fprintf(fid,'       %e \n',Y(i));
end

%genero el voxel
%if op_puntual~=1
fprintf(fid,'c Distribucion en el voxel \n');
fprintf(fid,'c  \n');
fprintf(fid,'c Tamaño voxel (cm) PET, dx: %g',tvoxel(1));
fprintf(fid,' dy=  %g',tvoxel(2));
fprintf(fid,' dz=  %g \n',tvoxel(3));
fprintf(fid,'c \n');
fprintf(fid,'si2 h  0.   ');
fprintf(fid,'  %g \n',tvoxel(1));
fprintf(fid,'sp2 d  0   1 \n');
fprintf(fid,'si3 h  0.  ');
fprintf(fid,'  %g \n',tvoxel(2));
fprintf(fid,'sp3 d  0   1 \n');
fprintf(fid,'si4 h  0.  ');
fprintf(fid,'  %g \n',tvoxel(3));
fprintf(fid,'sp4 d  0   1 \n');
%end 
%% distribucuion 
fprintf(fid,'c Voxeles Fuente \n');
fprintf(fid,'si5 l'); %distribucion 5 para que sean iguales 

% for i=1:size(A,3)
%     B(:,:,i)=A(:,:,i)'; 
% end 
corteN=1;
[ind_1]=find(A(:,:,:)>=corteN); %actividad
[y,x,z]=ind2sub([a,b,nslice],ind_1);

x=x-1;
y=y-1;
z=z-1; 

u=I(ind_1); %universos
u=u'; 
x=x'; 
y=y'; 
z=z';


n_total=size(x,2);

cell_1=ones(1,size(x,2)).*double((cell(end)+2));
cell_2=ones(1,size(x,2)).*double((cell(end)+1));

 
%% genero la fuente 
u=double(u);
%C=[u(1:n_prueba);cell_1(1:n_prueba);x(1:n_prueba);y(1:n_prueba);z(1:n_prueba);cell_2(1:n_prueba)];
C=[u;cell_1;x;y;z;cell_2];
formatSpec='       (%g<%g[ %g %g %g ]<%g) \n';

clc 
disp(' ')
disp(' Generando las posiciones de la fuente ...')

byte=fprintf(fid,formatSpec,C);
%fprintf(fid,'              (30<102[ 238 251 3 ]<101) ');

fprintf(fid,'c Se generaron N fuentes: %g \n',n_total);
%% genero las probabilidades

fprintf(fid,'c Probabilidades \n');
fprintf(fid,'sp5     ');

%ind= A(:,:,:)>corteN;
p=A(ind_1); %probabilidad 


formatSpec='            %e \n';

clc 
disp(' ')
disp(' Generando las posiciones de la fuente ...')

byte=fprintf(fid,formatSpec,p);

clc
% A=A./sum(A(:)); 

fprintf(fid,'c Se generaron N fuentes: %g ',n_total);

% cierro el archivo 
fclose(fid);
end 