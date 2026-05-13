function [I1]=f_pretumor(I1,index)
%UNTITLED Summary of this function goes here
%   Detailed explanation goes here

T1=I1==index.tumor;

T=uint8(T1);

pT=zeros(size(I1));
%figure(500)
for i=1:size(T1,3) 
      level = graythresh(T(:,:,i));
      BW_T = imbinarize(T(:,:,i), level);
      se = strel('disk',10);
      BW_pT = imdilate(BW_T,se);
      BW_pT(T1(:,:,i))=0; 
      pT(:,:,i)=BW_pT;
      
      %imshow(pT(:,:,i),[])
      %pause(0.1)
end

IND=pT==1; 

I1(IND)=index.pretumor; 