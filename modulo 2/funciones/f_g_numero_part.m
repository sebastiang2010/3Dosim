function status=f_g_numero_part(archivo)

fid=fopen(archivo, 'a+');
%%esta solo para tiempo 
%% se puede optimizar 

clc
parar=1;
while parar==1
disp(' ')    
%resp=input('Ingrese Tiempo (1) // Particulas (2)  '); 
resp=1; 

    switch resp
        case 1
            %disp('  ')
            %time=input('Ingrese el tiempo [m]: ');
            time=10; 
            fprintf(fid,'c tiempo [m] \n');
            fprintf(fid,'ctme ');
            fprintf(fid,'%g \n',time);
            parar=-1;
        case 2
            disp('  ')
            npart=input('Ingrese el numero de particulas: ');
            
            fprintf(fid,'c numero de particulas \n');
            fprintf(fid,'nps ');
            fprintf(fid,'%g \n',npart);
            parar=-1;
        otherwise
            disp('  ')
            disp(' El numero ingresado no es correcto ')
    end
end


%% cierro el archivo 
status=fclose(fid); %entrego el estatus al final 
