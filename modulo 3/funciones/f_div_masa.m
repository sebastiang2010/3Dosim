function D1=f_div_masa(D,Phantom,cell,masa)

D1=zeros(size(D));
for i=1:length(masa)
    D3=D;
    if cell==1; 
        A=Phantom==cell(i); %masa (i,1) index
        D2=ones(size(D));
        D3=zeros(size(D));
        D(A)=0;
    else 
    D2=ones(size(D)); 
    A=Phantom==cell(i); %masa (i,1) index
    D2(A)=masa(i);
    D3(~A)=0;
    D(A)=0; 
    end
     
    D1=D1+D3./D2;
end 
