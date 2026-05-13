function f_genero_materiales(mat,archivo,IdMat)

a=unique(IdMat(:));

fid=fopen(archivo, 'a+');

%fprintf(fid,'\n');
fprintf(fid,'c \n');
fprintf(fid,'c MATERIALES');
fprintf(fid,'\n');
for i=1:length(a)
    fprintf(fid,'c ');
    fprintf(fid,mat(a(i),1).Nombre);
    fprintf(fid,'\n');
    fprintf(fid,'c densidad [g/cm^3]: ');
    fprintf(fid,'  %g \n',mat(a(i),1).Densidad);
    comp=mat(a(i),1).Composicion;
    fprintf(fid,'c suma de composición: ');
    fprintf(fid,'  %g \n',abs(sum(comp(:,2))));
    fprintf(fid,'m');
    fprintf(fid,'%i',a(i));
    
    n1=1;
    for k=1:length(comp)
        if n1>1; fprintf(' ');end
        fprintf(fid,'          %g',comp(k,1));
        fprintf(fid,'            %g \n',comp(k,2));
        n1=n1+1;
    end
end
% 
% if op_fuente==3;
%     % material 201 acero inoxidable 
%     fprintf(fid,'c Materiales de la fuente');
%     fprintf(fid,'c ');
%     fprintf(fid,mat(201,1).Nombre);
%     fprintf(fid,'\n');
%     fprintf(fid,'c densidad [g/cm^3]: ');
%     fprintf(fid,'  %g \n',mat((201),1).Densidad);
%     comp=mat(201,1).Composicion;
%     fprintf(fid,'c suma de composición: ');
%     fprintf(fid,'  %g \n',abs(sum(comp(:,2))));
%     fprintf(fid,'m201');
%     n1=1;
%     for k=1:length(comp)
%         if n1>1; fprintf(' ');end
%         fprintf(fid,'          %g',comp(k,1));
%         fprintf(fid,'                %g \n',comp(k,2));
%         n1=n1+1;
%     end
%     % material de la fuente
%     fprintf(fid,'c Fuente: ');
%     fprintf(fid,fuentes(IdFuente,1).Nombre);
%     fprintf(fid,'\n');
%     fprintf(fid,'c densidad [g/cm^3]: ');
%     fprintf(fid,'  %g \n',fuentes(IdFuente,1).Densidad);
%     fprintf(fid,'m200');
%     fprintf(fid,' %g',fuentes(IdFuente).Z);
%     fprintf(fid,'  1');
%     fprintf(fid,'\n');

fclose(fid);
end




