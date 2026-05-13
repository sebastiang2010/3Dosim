BW = imread('blobs.png');
[B,L,N,A] = bwboundaries(BW);
figure; imshow(BW); hold on;
for k=1:length(B),
    if(~sum(A(k,:)))
       boundary = B{k};
       plot(boundary(:,2),...
           boundary(:,1),'r','LineWidth',2);
       for l=find(A(:,k))'
           boundary = B{l};
           plot(boundary(:,2),...
               boundary(:,1),'g','LineWidth',2);
       end
    end
end