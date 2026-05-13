function [bw_lung,bw_intestino,corte]=f_saco_lung(I1,corte)

bw_lung=zeros(size(I1));
bw_intestino=zeros(size(I1));


I1=imadjust(I1,[0 15000/35635],[]);
%h = fspecial('gaussian',5,3);
%I1= imfilter(I1,h,'replicate');


I1=imbinarize(I1);
I2=imfill(I1,'holes');

I3=I2-I1;

if I3==bw_intestino;corte=1;end

[B,~,N,~] =bwboundaries(I3);


bw_label = logical(I3);
%propiedades1=regionprops(bw_label,'centroid');
propiedades2=regionprops(bw_label,'area');
%propiedades3=regionprops(bw_label,'perimeter');

area=zeros(1,size(propiedades2,1));
for i=1:size(propiedades2,1)
    area(i)=propiedades2(i).Area;
end

ind=area<50;

for i=1:N
    if ind(i)==0
        boundary = B{i};
        %plot(boundary(:,2), boundary(:,1),'m','LineWidth',2);
        if corte==0
            for j=1:length(boundary)
                bw_lung(boundary(j,1),boundary(j,2))=1;
            end
        else
            for j=1:length(boundary)
                bw_intestino(boundary(j,1),boundary(j,2))=1;
            end
        end
    end

end

bw_lung=imfill(bw_lung,'holes');
bw_intestino=imfill(bw_intestino,'holes');

end % function




