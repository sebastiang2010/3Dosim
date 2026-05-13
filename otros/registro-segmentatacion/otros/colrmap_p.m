A=round(rand(100,100).*100);

max1=max(A(:));
min1=min(A(:));

div=4;
a=(max1-min1)/div;%no redondear
c=min1:a:max1;

nmap=max1; 
map=jet(64);
a=round(nmap/div);
map=map(1:a:64,:);


imshow(A)
colormap(map);
colorbar