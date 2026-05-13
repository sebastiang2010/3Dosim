function ok=f_genero_voxel_2(A,archivo)


%% Verosion 1.1 07/11/2017

%% como esta seleccionada a aca tomo todo
[fi,co,n]=size(A);
%n=3
nvoxel=fi*co*n;
%% abro el archivo
fid=fopen(archivo, 'a+'); % agrgar datos al archivo

n1=1; % inicio el conteo de lo que se graba
%% genero el voxel
cont=0;
cont1=0;
fprintf(fid, '      %d', A(1,1,1));  % Cambié %g a %d para enteros
cont = cont + 1;
r = -1;
b = A(1,1,1);
columna = 7 + length(num2str(A(1,1,1)));  % Cambié size(num2str(...)) por length(num2str(...))
h = waitbar(0, 'Generando el voxelizado...');
for i = 1:n
    w = A(:,:,i);
    waitbar(i/n)
    for l = 1:fi
        for m = 1:co
            cont1 = cont1 + 1;
            if b == w(l,m)
                r = r + 1;
            else
                if r >= 1
                    if r == 1
                        fprintf(fid, ' r');
                        cont = cont + 1;
                        columna = columna + 2;
                        if columna >= 50
                            fprintf(fid, '\n');
                            fprintf(fid, '     ');
                            n1 = 1;
                            columna = 7;
                        end
                        n1 = n1 + 1;
                    else
                        fprintf(fid, ' %d', r);  % Cambié %g a %d para enteros
                        fprintf(fid, 'r');
                        cont = cont + r;
                        columna = columna + 2 + length(num2str(r));  % Cambié size(num2str(...)) por length(num2str(...))
                        if columna >= 50
                            fprintf(fid, '\n');
                            fprintf(fid, '     ');
                            n1 = 1;
                            columna = 7;
                        end
                        n1 = n1 + 1;
                    end
                end
                if columna >= 50 
                    fprintf(fid, '\n');
                    fprintf(fid, '     ');
                    fprintf(fid, ' %d', w(l,m));  % Cambié %g a %d para enteros
                    cont = cont + 1;
                    columna = 7 + length(num2str(w(l,m)));  % Cambié size(num2str(...)) por length(num2str(...))
                    r = 0;
                    n1 = n1 + 1;
                else 
                    fprintf(fid, ' %d', w(l,m));  % Cambié %g a %d para enteros
                    cont = cont + 1;
                    columna = columna + 1 + length(num2str(w(l,m)));  % Cambié size(num2str(...)) por length(num2str(...))
                    r = 0;
                    n1 = n1 + 1;
                end 
            end
            
            b = w(l,m);
            
        end
        
    end
end
if r >= 1
    if r == 1
        fprintf(fid, ' r');
        cont = cont + 1;
        %n1=n1+1;
    else
        fprintf(fid, ' %d', r);  % Cambié %g a %d para enteros
        fprintf(fid, 'r');
        cont = cont + r;
    end
end
fprintf(fid, '\n');
close(h);


%% cierro el archivo
ok = -1;
if cont == nvoxel
    ok = 1;
    clc
    disp([' Se generaron: ', num2str(nvoxel, '%d')])  % Cambié %10.2e a %d para enteros
    disp(' ')
    disp(' El voxelizado se genero correctamente');
    disp('  '); 
    % disp(' INGRESE UNA TECLA PARA CONTINUAR'); 
    %pause(1)
    fprintf(fid, 'c se generaron:  ');
    fprintf(fid, '%d', nvoxel);  % Cambié %10.2e a %d para enteros
    fprintf(fid, '  voxels');
    fprintf(fid, '\n');
end
fclose(fid);
