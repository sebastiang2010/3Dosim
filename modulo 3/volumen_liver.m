clc 
close all 

I=paciente.Phantom;
index=paciente.index; 
vCT=paciente.vCT./10; %cm 

s=size(I); 

% figure(100)
% for i=1:s(3)
%     imshow(I(:,:,i),[])
%     colormap jet 
%     title(['Slice : ',num2str(i)])
%     pause(0.1)
% end 

IND_liver=I==index.liver; 
volumen=sum(IND_liver(:))*prod(vCT);



%figure(100)
for i=116:s(3)
    I1=I(:,:,i); 
    IND_liver=I1==index.liver; 

    I1(IND_liver)=index.tejido_blando; 
    I(:,:,i)=I1;
    %imshow(I(:,:,i),[])
    %title(['Slice : ',num2str(i)])
    %pause(0.1)
end 

figure(100)
for i=1:s(3)
    imshow(I(:,:,i),[])
    colormap jet 
    title(['Slice : ',num2str(i)])
    pause(0.1)
end 

IND_liver=I==index.liver; 
volumen=sum(IND_liver(:))*prod(vCT);