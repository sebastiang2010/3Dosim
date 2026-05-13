function [fill_bw]=f_sin_aire_exterior(I1)


I1 = imadjust(I1,[30000/65535 65535/65535],[]);

%BW=zeros(size(I1));
%h = fspecial('gaussian', hsize,sigma)
% figure(1)
% imshow(I1);
 %h = fspecial('gaussian',5,3);
 %I1= imfilter(I1,h,'replicate');
%  figure(2)
%  imshow(I1)
% T=0.5*(double(min(I1(:))+double(max(I1(:)))));
% done=false;
% while ~done
%     g=I1>=T;
%     Tnext=0.5*(mean(I1(g)))+mean(I1(~g));
%     done=abs(T-Tnext)<0.5;
%     T=Tnext;
% end
% T=T/255;
%[level,~] = graythresh(I1);
%BW = im2bw(I1,level); %#ok<IM2BW>
BW=imbinarize(I1); 

fill_bw=imfill(BW,'holes');

% figure(1)
% imshow(fill_bw)
% se = strel('disk',1);
% fill_bw=imerode(fill_bw,se);

se = strel('disk',8);
fill_bw=imclose(fill_bw,se); 

fill_bw= imdilate(fill_bw,se);


% clear BW
% 
% [B,~,~,~]=bwboundaries(fill_bw);
% 
% bw_camilla=zeros(size(I1));
% bw_label = logical(fill_bw);
% %propiedades1=regionprops(bw_label,'centroid');
% %propiedades2=regionprops(bw_label,'area');
% propiedades3=regionprops(bw_label,'perimeter');  




% %% 
% %imshow(bw_label)
% %hold on 
% 
% perimetro=zeros(1,size(propiedades3,1));
% for i=1:size(propiedades3,1)
%     perimetro(i)=propiedades3(i).Perimeter;
% end 
% 
% ind=max(perimetro)==perimetro; 
% 
% %
% for i=1:size(ind,2)
%     if ind(i)==0
%         boundary = B{i};
%         %plot(boundary(:,2), boundary(:,1),'m','LineWidth',2);
%         for j=1:length(boundary)
%             bw_camilla(boundary(j,1),boundary(j,2))=1;
%         end
%     end
%     
% end
% 
% bw_camilla=imfill(bw_camilla,'holes');


end % function




