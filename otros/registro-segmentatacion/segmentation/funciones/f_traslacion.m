
function [pos_fuente_2]=f_traslacion(archivo,pos_fuente,tvoxel,a,~,~)

%agregar s_new
%% abro el archivo 
fid=fopen(archivo, 'a+'); %agregar datos al archivo 
%%
% resto uno porque en MCNP empieza de (0,0,0)
pos_fuente=pos_fuente-1; 
%%
%pos_fuente=round(pos_fuente.*reduccion);
%%}
%pos_fuente_3(1)=pos_fuente(1);
%pos_fuente_3(2)=pos_fuente(2);
%pos_fuente_3(3)=pos_fuente(3);
%  Ojo agregar el s_new
%s_new(1)=512;
%s_new(2)=512;
%if size(corte)>0;
%   pos_fuente_3(1)=pos_fuente(1)-corte(1)+s_new(1)-corte(4);
%   pos_fuente_3(2)=pos_fuente(2)-corte(2)+s_new(2)-corte(3);
%end
%% como esta flipeado 
%if size(corte)==0
pos_fuente(2)=a(2)-pos_fuente(2); 
%end
%%
x_cm=pos_fuente(1)*tvoxel(1);
y_cm=pos_fuente(2)*tvoxel(2); 
z_cm=pos_fuente(3)*tvoxel(3);
%%
fprintf(fid,'  \n'); 
fprintf(fid,'c TRASLACION DE LA FUENTE  \n'); 
fprintf(fid,'tr1 ');
fprintf(fid,'  %g',x_cm);
fprintf(fid,'  %g',y_cm);
fprintf(fid,'  %g',z_cm);

pos_fuente_2=[x_cm,y_cm,z_cm]; 
end

