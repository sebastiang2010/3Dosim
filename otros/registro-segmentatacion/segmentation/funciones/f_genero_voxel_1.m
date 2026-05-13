function ok=f_genero_voxel_1(A,archivo)

%% como esta seleccionada a aca tomo todo
[fi,co,n]=size(A);
%n=3
nvoxel=fi*co*n;
%% abro el archivo
fid=fopen(archivo, 'a+'); %agrgar datos al archivo

n1=1; %inicio el conteo de lo que se graba
%% genero el voxel
cont=0;
cont1=0;
fprintf(fid,'      %g',A(1,1,1));
cont=cont+1;
r=-1;
b=A(1,1,1);
h = waitbar(0,'Generando el voxelizado...');
for i=1:n
    w=A(:,:,i);
    waitbar(i/n)
    for l=1:fi
        for m=1:co
            cont1=cont1+1;
            if b==w(l,m);
                r=r+1;
            else
                if r>=1;
                    if r==1;
                        fprintf(fid,' r');
                        cont=cont+1;
                        if n1>=10;
                            fprintf(fid,'\n');
                            fprintf(fid,'     ');
                            n1=1;
                        end
                        n1=n1+1;
                    else
                        fprintf(fid,' %g',r);
                        fprintf(fid,'r');
                        cont=cont+r;
                        
                        if n1>=10;
                            fprintf(fid,'\n');
                            fprintf(fid,'     ');
                            n1=1;
                        end
                        n1=n1+1;
                    end
                end
                fprintf(fid,' %g',w(l,m));
                cont=cont+1;
                r=0;
                n1=n1+1;
            end
            
            b=w(l,m);
            
        end
        
    end
end
if r>=1;
    if r==1;
        fprintf(fid,' r');
        cont=cont+1;
        %n1=n1+1;
    else
        fprintf(fid,' %g',r);
        fprintf(fid,'r');
        cont=cont+r;
    end
end
fprintf(fid,'\n');
close(h);


%% cierro el archivo
ok=-1;
if cont==nvoxel;
    ok=1;
    clc
    disp([' Se generaron: ',num2str(nvoxel,'%10.2e')])
    disp(' ')
    disp(' El voxelizado se genero correctamente');
    disp('  '); 
    % disp(' INGRESE UNA TECLA PARA CONTINUAR'); 
    pause(1)
    fprintf(fid,'c se generaron:  ');
    fprintf(fid,num2str(nvoxel,'%10.2e'));
    fprintf(fid,'  voxels');
    fprintf(fid,'\n');
end
fclose(fid);
%%
% cell=unique(A);
% for i=1:length(cell);
%     [x,y,z]=find(A(:,:,1)==cell(i));
%     
% end
end