function [BW] =f_seg_piel(I1);
%figure(2);
for i=1:size(I1,3)
    [level,em] = graythresh(I1(:,:,i));
    BW(:,:,i) = im2bw(I1(:,:,i),level);
    %imshow(BW(:,:,i),[]);
    %title(['Slice number # ',num2str(i)]);
    %pause(0.1)
end
% BW=double(BW);
% I1=double(Ioriginal); 
end

