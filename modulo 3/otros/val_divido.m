clear all
close all

Phantom=ones(300,300);
Phantom(50:60,100:200)=2;
Phantom(10:20,30:50)=3;
Phantom(150:200,150:200)=4;
D=ones(300,300).*20;
densidad=[5,5,5,5];
cell=[1,2,3,4];

D1=zeros(size(D));
for i=1:length(densidad)
    D3=D;
    if cell(i)==1; 
        A=Phantom==cell(i); 
        D2=ones(size(D));
        D3=zeros(size(D));
        D(A)=0;
    else 
    D2=ones(size(D)); 
    A=Phantom==cell(i); 
    D2(A)=densidad(i);
    D3(~A)=0;
    D(A)=0; 
    end
     
    D1=D1+D3./D2;
    
    figure(100)
    imshow(D,[])
    
    figure(101)
    imshow(D2,[])
    
    figure(102)
    imshow(D3,[])
    
    figure(103)
    imshow(D1,[])
end 