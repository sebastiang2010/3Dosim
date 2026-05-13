function [I1]=f_512_128(I,new,directorio)

numrows=new(1);
numcols=new(2);

clc
disp(' ')
op=input('Reducir tamaño de la imagen, Si (0) // No (~=0)  ');
if op==0;
    method='bilinear';
    %analizar intp3
    for i=1:size(I,3);
        I1(:,:,i)= imresize(I(:,:,i),[numrows numcols],method);
    end
    file=[directorio,'/imagen_reducida_128_mat.tif'];
    delete(file);
    for i=1:size(I1,3)
        imwrite(I1(:,:,i),file,'tiff','WriteMode','append')
    end
    clc
    disp('.......')
    disp('Se genero un tiff con la imagen reducida en el directorio :')
    disp(file)
else
    I1=I;
end

end

