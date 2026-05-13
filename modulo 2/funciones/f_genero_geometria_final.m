function f_genero_geometria_final(archivo,a,tvoxel)
%% tvoxel mm 

%% abro el archivo 
fid=fopen(archivo, 'a+'); %agrgar datos al archivo 
%%
tvoxel=quant(tvoxel,0.001); 

xm=a(1)*tvoxel(1)/10; %cm 
ym=a(2)*tvoxel(2)/10; %cm 
zm=a(3)*tvoxel(3)/10; % cm 
%% genero lo que va luego del voxel 
%if op_fuente==1 || op_fuente==2;


fprintf(fid,'9999   0   1    imp:p=0  imp:e=0 \n');

% else
%    fprintf(fid,'c Fuente de: ');
%    fprintf(fid,fuentes(IdFuente,1).Nombre);
%    fprintf(fid,'\n'); 
%    fprintf(fid,'700 200');
%    fprintf(fid,'  -%g',fuentes(IdFuente,1).Densidad);
%    fprintf(fid,'   -180 imp:p=1 imp:e=0 trcl=1 $cilindro interior fuente "Acticvidad" \n');
%    fprintf(fid,'c exterior de acero inoxidable \n');
%    fprintf(fid,'701 201  -7.9   -170 180 imp:p=1 imp:e=0 trcl=1 $cilindro exterior\n'); 
%    fprintf(fid,'9998 0          -1 #700 #701 fill=');
%    fprintf(fid,'%g',2*length(cell)+1); 
%    fprintf(fid,' imp:p=1 imp:e=1 \n');
%    fprintf(fid,'9999 0          1   imp:p=0 imp:e=0 \n');
% end
fprintf(fid,'\n');
%% superficie universo 1
fprintf(fid,'c Superficies \n'); 
fprintf(fid,'c Tamaño del voxel:  ' );
fprintf(fid,' dx= %g',tvoxel(1)/10);
fprintf(fid,' dy= %g',tvoxel(2)/10);
fprintf(fid,' dz= %g \n',tvoxel(3)/10);
fprintf(fid,'c Tamaño de la imagen:  '); 
fprintf(fid,'[ %g',a(1));
fprintf(fid,' %g',a(2));
fprintf(fid,' %g ] \n',a(3));
fprintf(fid,'c \n');
fprintf(fid,'1   rpp  0.');
fprintf(fid,'  %g',xm);
fprintf(fid,' 0.');
fprintf(fid,'  %g',ym);
fprintf(fid,' 0.');
fprintf(fid,'  %g \n',zm);

%% universo 2
fprintf(fid,'2   rpp  0. ');
fprintf(fid,' %g',tvoxel(1)/10);
fprintf(fid,' 0.');
fprintf(fid,' %g',tvoxel(2)/10);
fprintf(fid,' 0.');
fprintf(fid,' %g',tvoxel(3)/10);
fprintf(fid,' \n'); 

% if op_fuente==3;
%     fprintf(fid,'c Fuente real SESAME \n');
%     fprintf(fid,'170 rcc  0  0  0         0  0  0.6     0.2  $cilindro exterior   \n');
%     fprintf(fid,'180 rcc  0  0  0.2       0  0  0.2     0.1  $cilindro interior fuente \n');
% end    
    
%% cierro el archivo
fclose(fid);

end
