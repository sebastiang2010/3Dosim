clc 
clear all 
close all 

I = imread('coins.png');
Ibw = im2bw(I);
figure(1)
imshow(Ibw,[])

Ibw = imfill(Ibw,'holes');
figure(2)
imshow(Ibw,[])

Ilabel = bwlabel(Ibw);
stat = regionprops(Ilabel,'centroid');

stat2 = regionprops(Ilabel,'area');

for i=1:length(stat2)
    area(i)=stat2(i).Area;
end

max1=max(area);
ind=find(max1==area);








imshow(I); hold on;
for x = 1: numel(stat)
    plot(stat(x).Centroid(1),stat(x).Centroid(2),'ro');
end