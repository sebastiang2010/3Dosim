function sum_emisividad=f_genero_fuente_2(archivo,pos_fuente_2,idfuente,fuentes,pos_fuente,image_size)


fid=fopen(archivo, 'a+'); %agregar datos al archivo

%funete de gammagrafia solo par=2
E=fuentes(idfuente,1).E;
Y=fuentes(idfuente,1).Yield;
Nombre=fuentes(idfuente,1).Nombre;
emisividad=sum(Y(:)); 


dz=0.3; % Ojo este es para la fuente en particular que pusimos

fprintf(fid,'c \n');
fprintf(fid,'c FUENTE \n');
fprintf(fid,'c Posición MATLAB');
fprintf(fid,' [%g',pos_fuente(1));
fprintf(fid,' %g',pos_fuente(2));
fprintf(fid,' %g] \n',pos_fuente(3));
fprintf(fid,'c Posición MCNP');
fprintf(fid,' [%g',pos_fuente(1)-1);
fprintf(fid,' %g',image_size(2)-pos_fuente(2));
fprintf(fid,' %g] \n',pos_fuente(3)-1);
fprintf(fid,'c \n');
fprintf(fid,'sdef erg d1 pos');
fprintf(fid,'  %g',pos_fuente_2(1));
fprintf(fid,'  %g',pos_fuente_2(2));
fprintf(fid,'  %g',pos_fuente_2(3)+dz);
fprintf(fid,' axs 0 0 1  rad d2 ext d3 cell 700 par 2 \n');
fprintf(fid,'c Fuente de ');
fprintf(fid,Nombre);
fprintf(fid,'\n');
sum_emisividad=sum(Y(:));
fprintf(fid,'c sum emisividad:  %g \n',emisividad);
%fprintf(fid,'  // normalizado \n');
fprintf(fid,'c    E [MeV]     Emisividad \n');
fprintf(fid,'#    si1         sp1 \n');
fprintf(fid,'       l          d   \n');
for i=1:length(E);
    fprintf(fid,'    %e',E(i));
    fprintf(fid,'    %e \n',Y(i));
end
fprintf(fid,'c Radio de la fuente \n');
fprintf(fid,'si2  0  0.1 \n'); 
fprintf(fid,'sp2  0  1  \n');  
fprintf(fid,'c Extensión de la fuente \n');
fprintf(fid,'si3  -0.1  0.1 \n'); 
fprintf(fid,'sp3  0  1'); 
%% cierro el archivo 
fclose(fid);
end 

