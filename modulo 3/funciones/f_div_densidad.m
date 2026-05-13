function D1=f_div_densidad(D,Phantom,cell,densidad)

D1=zeros(size(D));
for i=1:length(densidad)
    D3=D;
    %if cell(i)==1 % asigan dosis cero al aire 
    %    A=Phantom==cell(i); 
    %    D2=ones(size(D));
    %    D3=zeros(size(D));
    %    D(A)=0;
    %else 
    D2=ones(size(D)); 
    A=Phantom==cell(i); 
    D2(A)=densidad(i);
    D3(~A)=0;
    D(A)=0; 
    %end
     
    D1=D1+D3./D2;
end 
