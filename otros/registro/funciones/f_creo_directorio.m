function directorio=f_creo_directorio

if ispc==1;
    currentdirectory=pwd;
    addpath(currentdirectory);
    %
    directorio='c:/MAT/';
    directorio1='d:/MAT/3Dosim';
    
    direct=dir(directorio);
    n=size(direct,1);
    
    direct=dir(directorio1);
    n1=size(direct,1);
    %%%%%%%%%%%%%%
    if n>0;
        %direct=directorio;
        return
    end
    if n1>0;
        directorio=directorio1;
        return
    end
    
    parar=1;
    while parar==1
        clc
        disp('         ');
        disp('Ingrese: ');
        disp('        1 si desea crear C:\MAT\3Dosim');
        disp('        2 si desea crear D:\MAT\3Dosim');
        a=input('Respuesta : ');
        verdadero=[1,2];
        ind=find(a==verdadero, 1);
        if isempty(ind);
            clc
            disp(' No es un valor correcto');
        else
            parar=-1;
        end
    end
    
    if a==1;
        
        directorio='c:/MAT/3Dosim';
        [s,mess,messid]=mkdir(directorio);
        if s==1;
            clc
            disp('   ')
            disp('Se creo el directorio: ')
            disp(directorio)
        else
            disp('   ');
            disp(mess)
            dips('   ')
            dips(messid)
        end
    else
        directorio='d:/MAT/3Dosim';
        [s,mess,messid]=mkdir(directorio);
        if s==1;
            
        else
            clc
            disp('   ')
            disp(mess)
            dips('   ')
            dips(messid)
        end
    end
    
end

%% caso Unix
if isunix==1;
    currentdirectory=pwd;
    addpath(currentdirectory);
    %
    directorio='/Home/MAT/3Dosim';
    
    direct=dir(directorio);
    n=size(direct,1);
    
    %%%%%%%%%%%%%%
    if n>0;
        %direct=directorio;
        return
    else
        [s,mess,messid]=mkdir(directorio);
        if s==1;
            clc
            disp('   ')
            disp('Se creo el directorio: ')
            disp(directorio)
        else
            disp('   ');
            disp(mess)
            dips('   ')
            dips(messid)
        end
    end
end


