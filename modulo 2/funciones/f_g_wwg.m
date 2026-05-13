function f_g_wwg(archivo,pos,size,tvoxel)

% es en particular para la funte general 
fid=fopen(archivo, 'a+'); %agregar datos al archivo

fprintf(fid,' \n');
fprintf(fid,'c ------- \n');
fprintf(fid,'c Weight-Window \n');
fprintf(fid,'wwg 8 0 0 \n');
fprintf(fid,'mesh geom=rec ,\n');
fprintf(fid,'     ref=      %g',pos(1));
fprintf(fid,'     %g ',pos(2));
fprintf(fid,'     %g \n',pos(3)+0.3);
fprintf(fid,'     origin=  -0.1     -0.1  -0.1 \n');
fprintf(fid,'     imesh=        0     %g \n',size(2)*tvoxel(2));
%fprintf(fid,'     iints=        1     %g \n',size(2)/2);
fprintf(fid,'     iints=        1     %g \n',size(2));
fprintf(fid,'     jmesh=        0     %g \n',size(1)*tvoxel(1));
% fprintf(fid,'     jints=        1     %g \n',size(1)/2);
fprintf(fid,'     jints=        1     %g \n',size(1));
fprintf(fid,'     kmesh=        0     %g \n',size(3)*tvoxel(3));
fprintf(fid,'     kints=        1     %g \n',size(3));
fprintf(fid,'wwp:p 4j 1');
fclose(fid);




















end % function