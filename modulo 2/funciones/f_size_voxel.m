function [tvoxel]=f_size_voxel(tvoxel)

%t_voxel_o cm 

clc
disp(' ')
dx=input('Indicates voxel dimension dx[mm]: ');
disp(' ')
dy=input('Indicates voxel dimension dy[mm]: ');
disp(' ')
dz=input('Indicates voxel dimension dz[mm]: ');

tvoxel=[dx dy dz]; 
tvoxel=tvoxel./10;% cm a mm

%reduccion=tvoxel./tvoxel_o; 

%s_new=ceil(s_o./reduccion); 

%tvoxel_r=s_o.*tvoxel_o./s_new;

%tvoxel_r=tvoxel_r./10; % size en cm 


clc
end