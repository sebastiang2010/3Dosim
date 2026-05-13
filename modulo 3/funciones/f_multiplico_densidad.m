function D1=f_div_densidad(D,Phantom,densidad)

D1=zeros(size(D));
for i=1:length(densidad)
    D3=D;
    D2=ones(size(D)); 
    ind=Phantom==densidad(i,1); %densidad (i,1) index
    D2(ind)=densidad(i,2);
    D3(~ind)=0;
    if densidad(i,1)==1; 
        D2=ones(size(D));
        D3(ind)=0;
        D(ind)=0;
    end
    D1=D1+D3./D2;
end

% figure(100)
% imshow(D1(:,:,n),[])
% colormap(jet)
% n=n+1;
% pause