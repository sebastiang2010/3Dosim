function fid=f_genero_titulo(archivo,version,PatientID)

fecha=date;
hora=fix(clock); 
fid=fopen(archivo, 'a+'); %agregar datos al archivo
if  size(num2str(hora(5)),2)==1;a=['0',num2str(hora(5))];else a=num2str(hora(5));end

fprintf(fid,'.................................................................. \n');
fprintf(fid,'.................................................................. \n');
fprintf(fid,' Archivo generado con 3Dosim, version ');
fprintf(fid,version);
fprintf(fid,' \n');
fprintf(fid,' Fecha : ');
fprintf(fid,fecha);
fprintf(fid,' %g',hora(4));
fprintf(fid,':');
fprintf(fid,'%g hs \n',str2double(a));
fprintf(fid,'.................................................................. \n');
fprintf(fid,' Paciente ID =   %s \n',PatientID);
fprintf(fid,'.................................................................. \n');

end 