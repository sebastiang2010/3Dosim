function [sum_emisividad,particula]=f_genero_fuente_1(archivo,tvoxel,cell,I,ncell_fuente,idfuente,fuentes)


fid=fopen(archivo, 'a+'); %agregar datos al archivo

E=fuentes(idfuente,1).E;
Y=fuentes(idfuente,1).Yield;
Nombre=fuentes(idfuente,1).Nombre; 
particula=fuentes(idfuente,1).par;

fprintf(fid,'c FUENTE \n');
% fprintf(fid,'sdef erg d1 x d2 y d3  z d4  cell d5  par=2 \n');% la energia como una distribucion
fprintf(fid,'sdef erg d1 x %g',tvoxel(1)/2); %la posicion de la fuente en el centro del voxel 
fprintf(fid,' y %g',tvoxel(2)/2);
fprintf(fid,' z %g',tvoxel(3)/2);
fprintf(fid,' cell d2 par %g',particula); 
fprintf(fid,' /n'); 
fprintf(fid,'c Fuente de ');
fprintf(fid,Nombre);
fprintf(fid,'\n');
sum_emisividad=sum(Y(:));
fprintf(fid,'c sum emisividad :%g \n',sum(Y(:)));
fprintf(fid,'#    si1   sp1 \n');
fprintf(fid,'       l          d   \n');
for i=1:length(E);
    fprintf(fid,'       %e',E(i));
    fprintf(fid,'       %e \n',Y(i));
end
% fprintf(fid,'si2 h  0.');
% fprintf(fid,'  %g \n',tvoxel(1));
% fprintf(fid,'sp2 d  0   1 \n');
% fprintf(fid,'si3 h  0.');
% fprintf(fid,'  %g \n',tvoxel(2));
% fprintf(fid,'sp3 d  0   1 \n');
% fprintf(fid,'si4 h  0.');
% fprintf(fid,'  %g \n',tvoxel(3));
% fprintf(fid,'sp4 d  0   1 \n');
%% Voxeles fuente 
fprintf(fid,'c Voxeles Fuente \n');
fprintf(fid,'si2 l');

n=1;
nv_fuente=0;
linea=1; %que er esto 
h=waitbar(0,'Generando la fuente...');
nslice=size(I,3);
for k=1:nslice
    waitbar(k/nslice);
    [x,y]=find(I(:,:,k)'==ncell_fuente);
    x=x-1;
    y=y-1;
    z=k-1;
    nv_fuente=nv_fuente+length(x);
    
    for i=1:length(x);
        if linea==1;
            if n==1
                fprintf(fid,'  (%g',ncell_fuente);
            else
                fprintf(fid,'  (%g',ncell_fuente);
            end
        end
        
        if linea==2;
            if n==1
                fprintf(fid,'       (%g',ncell_fuente);
            else
                fprintf(fid,'  (%g',ncell_fuente);
            end
        end
        fprintf(fid,'<%g',cell(end)+2);
        fprintf(fid,'[%g',x(i));
        fprintf(fid,' %g',y(i));
        fprintf(fid,' %g',z);
        fprintf(fid,']');
        fprintf(fid,'<%g',cell(end)+1);
        fprintf(fid,')');
        
        if n==2;
            fprintf(fid,'\n');
            linea=2;
            n=1;
        else
            n=n+1;
        end
    end
end
if n==2;fprintf(fid,'\n');end
fprintf(fid,'c Probabilidades \n');
fprintf(fid,'sp2  1');
fprintf(fid,' %g',nv_fuente-1);
fprintf(fid,'r');

close(h)



%% cierro el archivo 
fclose(fid);
end 