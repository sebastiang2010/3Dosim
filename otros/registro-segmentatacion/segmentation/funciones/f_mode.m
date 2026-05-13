function [mode,a]=f_mode(archivo,tvoxel,fuentes)

fid=fopen(archivo, 'a+');

IdFuente=1; %unica que hay 

E=fuentes(IdFuente,1).E;
a=ceil(max(E(:)));  %ceil redondea a +inf 

%clc
parar=1;
while parar==1;
    %clc
    %disp(' ')
    %resp=input('Ingrese mode p e (1) // mode p (2):  ');
    resp=1; 
    switch resp
        case 1
            mode=1; 
            cut=f_cut(tvoxel);
            fprintf(fid,' \n');
            fprintf(fid,'c \n');
            fprintf(fid,'c MODDE \n');
            fprintf(fid,'phys:p  %g',a); % maxima energia para fotones hay que buscar el maximo de energia.
            fprintf(fid,' \n');
            fprintf(fid,'phys:e %g',a');
            fprintf(fid,' 12j 0.99 $MCNP 6.0 \n'); 
            fprintf(fid,'c phys:e %g',a');
            fprintf(fid,' 9j 0.99 $MCNPX \n'); %efac=0.99 
            fprintf(fid,'mode p e \n');
            fprintf(fid,'c cut:e j');
            fprintf(fid,' %g',cut);
            fprintf(fid,' \n');
            parar=-1;
        case 2
            mode=2;
            fprintf(fid,' \n');
            fprintf(fid,'c MODDE \n');
            fprintf(fid,'mode p \n');
            parar=-1;
        otherwise
            disp('  ')
            disp(' El numero ingresado no es correcto ')
    end
end
%% cierro el archivo 
fclose(fid);
end


