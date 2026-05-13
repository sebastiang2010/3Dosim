function f_genero_geometria_1(cell,mat,archivo,a,idMat,flip)

%fecha=date;
%hora=fix(clock); 
cierro_u=8000;
u_fill=1000;

fid=fopen(archivo, 'a+'); %agregar datos al archivo

%fprintf(fid,'Fecha : ');
%fprintf(fid,fecha);
%fprintf(fid,' %g',hora(4));
%fprintf(fid,':');
%fprintf(fid,'%g hs \n',hora(5));
%fprintf(fid,'c  \n');
fprintf(fid,'c Flip=');
fprintf(fid,'  %g\n',flip);
fprintf(fid,'c   \n');
fprintf(fid,'c Universos \n');
%% primera linea
fprintf(fid,'%g',cell(1));
fprintf(fid,'    %g',idMat(1));
fprintf(fid,'   -%g',mat(idMat(1)).Densidad);
fprintf(fid,'   -2'); %interior de la celda 2 (macro cuerpo pequeño)
fprintf(fid,'   u=');
fprintf(fid,'%g',cell(1));
fprintf(fid,'   imp:p=1 imp:e=1 $ ');
fprintf(fid,mat(idMat(1)).Nombre);
fprintf(fid,' \n');
%% las celdas que siguen
n=length(cell);
for i=2:n
    fprintf(fid,'%g ',cell(i));
    fprintf(fid,'     like');
    fprintf(fid,'  %g',cell(1));
    fprintf(fid,'   but');
    fprintf(fid,'     mat=');
    fprintf(fid,'%g',idMat(i));
    fprintf(fid,'    rho=');
    fprintf(fid,'-%g',mat(idMat(i),1).Densidad);
    fprintf(fid,'    u=');
    fprintf(fid,'%g',cell(i));
    fprintf(fid,'   imp:p=1 imp:e=1 $  ');
    fprintf(fid,mat(idMat(i),1).Nombre);
    fprintf(fid,' \n');
end
%% pongo vacio al resto del universo 

for i=1:n
    fprintf(fid,'%g',double(cell(i))+cierro_u);
    fprintf(fid,'     0   2   u=');
    fprintf(fid,'%g',cell(i));
    fprintf(fid,'  imp:p=0 imp:e=0 $cierro los universos\n');
    %fprintf(fid,'   \n')
end
% if op_fuente==1 || op_fuente==2;
    fprintf(fid,'%g',u_fill);
    fprintf(fid,'   0             -1          ');
    fprintf(fid,'fill=%g',u_fill);
    fprintf(fid,'     imp:p=1 imp:e=1 \n');
    fprintf(fid,'%g',u_fill+1);
    fprintf(fid,'   0             -2         lat=1   ');
    fprintf(fid,'u=%g',u_fill);
    fprintf(fid,'     imp:p=1 imp:e=1 \n');
    fprintf(fid,'                                 fill=0:');
    fprintf(fid,'%g',a(1)-1);
    fprintf(fid,' 0:');
    fprintf(fid,'%g',a(2)-1);
    fprintf(fid,' 0:');
    fprintf(fid,'%g \n',a(3)-1);
% else
%     fprintf(fid,'%g',max(cell)+1);
%     fprintf(fid,'   0             -2         lat=1   ');
%     fprintf(fid,'u=%g',max(cell)+1);
%     fprintf(fid,'     imp:p=1 imp:e=1 \n');
%     fprintf(fid,'                                 fill=0:');
%     fprintf(fid,'%g',a(1)-1);
%     fprintf(fid,' 0:');
%     fprintf(fid,'%g',a(2)-1);
%     fprintf(fid,' 0:');
%     fprintf(fid,'%g \n',a(3)-1);
% end
%% cierro el archivo
fclose(fid);
end 