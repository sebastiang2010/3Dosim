sI=size(I); 

nslice=100;

figure(100)
imshow(A(:,:,nslice),[])

A=uint8(A); 
figure(101)
imshow(A(:,:,nslice),[]);

A1=imbinarize(A);
figure(102)
imshow(A1(:,:,nslice),[]);

se = strel('square',10);
for i=1:sI(3)
   A2(:,:,i)=imfill(A1(:,:,i),4,'holes');
   A2(:,:,i)=imdilate(A2(:,:,i),se);
end 


% figure(104)
% for i=1:sI(3)
%   imshow(A2(:,:,i),[]);
%     pause(0.1)
% end 

IND=A2>0;
A2(IND)=index.liver;
I(IND)=0; 

Phantom(IND)=0; % por si toque alguna estructura 
Phantom=Phantom+double(A2); 

figure(104)
for i=1:sI(3)
    imshow(Phantom(:,:,i),[]);
    pause(0.1)
end 



figure(105)
imshow(Phantom(:,:,nslice),[])

