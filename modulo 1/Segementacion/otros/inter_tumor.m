I=zeros(200,200,15); 
I(50:70,80:100,5)=1; 
I(40:90,100:150,10)=1;
I(50:70,80:100,13)=1; 

figure(1)
for i=1:15 
    imshow(I(:,:,i),[])
    pause(0.2)
end 

s_n=size(I);
s_n(3)=100;
I1=f_inter3D(I,s_n);

figure(1)
for i=1:15 
    imshow(I1(:,:,i),[])
    pause(0.3)
end 

a=I1==1; 
sum(a(:));
