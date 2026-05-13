function [maks]=f_saco_hueso(I1)

I1=imadjust(I1,[60000/65535 1],[]); 
h = fspecial('gaussian',5,3);
I1= imfilter(I1,h,'replicate');

clusters=2;
[~,maks]=f_kmeans(I1,clusters); % tratar de entenderla bien 

% binario 
ind=maks==1; 
maks(ind)=0;

ind=maks==2; 
maks(ind)=1;


end % function 




