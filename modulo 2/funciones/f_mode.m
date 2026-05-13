function [mode,a]=f_mode(archivo,fuentes)

fid=fopen(archivo, 'a+');

IdFuente=1; %unica que hay

E=fuentes(IdFuente,1).E;
a=ceil(max(E(:)));  %ceil redondea a +inf

mode='mode e'; %

fprintf(fid,' \n');
fprintf(fid,'c \n');
fprintf(fid,'c MODDE \n');
fprintf(fid,'phys:e %g',a');
fprintf(fid,' 12j 0.99 $MCNP 6.0 \n');
fprintf(fid,'c phys:e %g',a');
fprintf(fid,' 9j 0.99 $MCNPX \n'); %efac=0.99
fprintf(fid,'mode e \n');

%% cierro el archivo
fclose(fid);
end


