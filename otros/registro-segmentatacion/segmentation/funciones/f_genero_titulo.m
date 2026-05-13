function f_genero_titulo(archivo,version)

fecha=date;
hora=fix(clock); 
fid=fopen(archivo, 'a+'); %agregar datos al archivo
if  size(num2str(hora(5)),2)==1;a=['0',num2str(hora(5))];else a=num2str(hora(5));end

fprintf(fid,'c ------------------------------------------------------ \n');
fprintf(fid,'c ------------------------------------------------------ \n');
fprintf(fid,'c Archivo generado con 3Dosim, version ');
fprintf(fid,version);
fprintf(fid,' \n');
fprintf(fid,'c Fecha : ');
fprintf(fid,fecha);
fprintf(fid,' %g',hora(4));
fprintf(fid,':');
fprintf(fid,'%g hs \n',str2double(a));
fprintf(fid,'c ------------------------------------------------------  \n');
fprintf(fid,'c ------------------------------------------------------  \n');
%% cierro el archivo
fclose(fid);
end 