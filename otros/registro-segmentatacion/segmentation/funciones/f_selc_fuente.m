function idfuente=f_selc_fuente(fuente)


for i=1:length(fuente); %menos 1 porque la ultima es el aire con 256
    clc
    disp(' Fuentes disponibles');
    disp('.....')

    for j=1:length(fuente);
        disp([fuente(j,1).Nombre,' : ',num2str(j)]);
    end
end    
    parar=-1;
    while parar==-1;
        %idfuente=round(rand*5+1);
        idfuente=input(' Ingrese el numero de la fuente:  ');
        if idfuente<=length(fuente) && idfuente>0;
            parar=1;
        else 
           disp(' El numero seleccionado no es valido') 
        end
    end
    
    clc