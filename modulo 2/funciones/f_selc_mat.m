function idmat=f_selc_mat(cell,index)

% Importante los materiales van hasta 200 para el ICRP y
% Apartir del 200 los de la fuente

% clc
% disp([' La celda ',num2str(n_aire),' corresponde a aire']);
% disp('.....')
% pause(1);
clc
%m=1;

idmat=ones(1,size(cell,1));
for i=1:size(cell,1)
    %     a=0;
    %     clc
    %     %if cell(i)~=n_aire
    %         disp(' Lista de materiales')
    %         disp(' .....')
    %         for j=1:length(mat);
    %             if ~isempty(mat(j,1).Id) && mat(j,1).Id<201
    %                disp([mat(j,1).Nombre,' : ',num2str(j)]);
    %                a=a+1;
    %             end
    %         end
    %
    %         disp('.....')
    %         disp(['Material de la celda  :',num2str(cell(i))]);
    %         disp('.....')
    %         disp('.....')
    %         parar=-1;
    %
    %         while parar==-1;
    %             %n=round(rand*14)+1;
    %             n=input(' Ingrese el numero del material:  ');
    %             if n<=a && n>0;
    %                 idmat(i)=n;
    %                 parar=1;
    %
    %             else disp(' El numero seleccionado no es valido')
    %
    %             end
    %         end
    %     %end
    % end
    
    if cell(i)==index.aire;idmat(i)=1;end % aire
    if cell(i)==index.tejido_blando;idmat(i)=2;end % tejido blando
    if cell(i)==index.liver;idmat(i)=3;end % higado
    if cell(i)>=index.tumor;idmat(i)=4;end % tumor
    if cell(i)==index.hueso;idmat(i)=6;end %bone 
    if cell(i)==index.lung;idmat(i)=5;end % lung 
end
clc
disp(' ')
disp(' Se asignaron los materiales  ')
pause(0.5)

clc
