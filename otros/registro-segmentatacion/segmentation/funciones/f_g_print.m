function f_g_print(archivo)

fid=fopen(archivo, 'a+');

fprintf(fid,'c \n')
fprintf(fid,'c PRINT \n'); 
fprintf(fid,'print -85 -86 -128\n'); %saco estas tablas
%fprintf(fid,'prdmp 2j 1 1 j \n'); % me genera el archivo m 
%fprintf(fid,'dbcn 2j 1 50 \n');  % me muestra la historia de las particulas 
%fprintf(fid,'prdmp -60 -60 1 1 \n');
fprintf(fid,'prdmp 0 -60 1 1\n'); % genera solo la ultima impresion pero guarda info cada 60
fprintf(fid,'ptrac file=asc event=src write=all \n'); %genera el ptrac de la fuente
fclose(fid);
end
