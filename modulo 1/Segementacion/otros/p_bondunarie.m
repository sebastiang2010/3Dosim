I=zeros(512,512);
I(100:110,200:210)=1; 
I(300:400,300:400)=1; 
A1=zeros(512,512);
A2=zeros(512,512);

close all 
figure(1)
imshow(I,[]);
hold on 
[B,L,N,A] = bwboundaries(I);
for k=1:length(B{1,1}) 
    B1=B{1,1};
    plot(B1(k,2),B1(k,1),'g')
    A1(B1(k,1),B1(k,1))=1;
end
A2(B1(:,1),B1(:,2))=1;

figure(2)
imshow(A1)
figure(3)
imshow(A2)



% BW = imread('blobs.png');
% [B,L,N,A] = bwboundaries(BW);
% figure; imshow(BW); hold on;
% for k=1:length(B),
%     if(~sum(A(k,:)))
%        boundary = B{k};
%        plot(boundary(:,2),...
%            boundary(:,1),'r','LineWidth',2);
%        for l=find(A(:,k))'
%            boundary = B{l};
%            plot(boundary(:,2),...
%                boundary(:,1),'g','LineWidth',2);
%        end
%     end
% end