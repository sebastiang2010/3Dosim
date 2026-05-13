function [I,cell_o]=f_re_cell(I,cell_o,op)

if op==1
    cell_o=unique(I(:)); 
    n=length(cell_o);
    cell_new=1:n;
    for i=1:n
        I(I==cell_o(i))=cell_new(i);
    end   
else
   cell=unique(I(:)); 
   A=I;
   I=zeros(size(A));
   n=length(cell_o);
   for i=1:n
       %figure(500)
       %imshow(A(:,:,5),[])
       %colormap(jet)
       ind=A==cell(i);
       I(ind)=cell_o(i);
       %figure(501)
       %imshow(I(:,:,5),[])
       %colormap(jet)
    end   
end

