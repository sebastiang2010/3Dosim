function op_fuente=f_ask_fuente

a=[1 2 3];

parar=1;
while parar==1;
    clc
    disp('   ');
    disp(' Fuente Voxelizada Uniforme: 1 ');
    disp(' Fuente Voxelizada No Uniforme: 2 ');
    disp(' Fuente Geometrica (gammagrafia): 3 ');
    disp('  ');
    op_fuente=input(' Ingrese opcion: ');
    
    a1=op_fuente==a;
    
    if sum(a1)==1;
        parar=-1;
    else 
        disp('  ');
        disp(' La opcion no es correcta');
    end
end
clc
end