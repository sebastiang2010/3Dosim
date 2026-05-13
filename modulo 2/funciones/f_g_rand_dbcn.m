function f_g_rand_dbcn(archivo)

seed=f_rand; 
fid=fopen(archivo, 'a+');

fprintf(fid,'c \n');
fprintf(fid,'c RAND \n'); 
fprintf(fid,'rand stride=1111152917 gen=2');
fprintf(fid,' seed= %u \n',seed); 
fprintf(fid,'c DBCN \n');
fprintf(fid,'dbcn 48j 1 \n'); 
fclose(fid);
end
