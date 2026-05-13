function ncell_fuente=f_selc_cell_fuente(cell) 


 clc
 disp(' Celdas disponibles');
 disp('.....')
 for i=1:length(cell) 
     disp([' Celda : ',num2str(cell(i))]);   
 end

 %ncell_fuente=input(' Ingrese la celda que desea utilizar como fuente: ');
 parar=1; 
 while parar==1; 
       ncell_fuente=input(' Ingrese la celda que desea utilizar como fuente: ');
       a=find(cell==ncell_fuente);
       if isempty(a)
          disp(' No es una celda disponible')
       else
           parar=-1; 
       end 
 end
 
 clc