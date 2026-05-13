clear all 
close all 
clc

load mri; 
D=squeeze(D); 

[faces,verts]=isosurface(D,0.5); 

patch('Vertices', verts, 'Faces', faces)%, ... 
   % 'FaceVertexCData', colors, ... 
   % 'FaceColor','interp', ... 
   % 'edgecolor', 'interp');
view(30,-15);
axis vis3d;
colormap copper

tvoxel=[1,1,1]; 

v1=verts(:,3);

for slice=1:size(D,3)
    ind=find(v1==slice);
    v=verts(ind,:);
    
    figure(3)
    imshow(D(:,:,slice),[])
    hold on
    scatter(v(:,1),v(:,2));
    
    pause(1)
end