function [tvoxel]=f_tvoxel(tvoxel)

if isempty(tvoxel)
    clc
    disp(' ')
    dx=input('  Indicates voxel dimension dx[mm]: ');
    disp(' ')
    dy=input('  Indicates voxel dimension dy[mm]: ');
    disp(' ')
    dz=input('  Indicates voxel dimension dz[mm]: ');
    
    
    tvoxel=[dx dy dz];
    %tvoxel=tvoxel;% mm
    
else
    clc
    disp(' ')
    disp([' Voxel dimension dx[mm]: ',num2str(tvoxel(1))]);
    disp(' ')
    disp([' Voxel dimension dy[mm]: ',num2str(tvoxel(2))]);
    disp(' ')
    disp([' Voxel dimension dz[mm]: ',num2str(tvoxel(3))]);
    disp(' ' )
    op=input(' Quiere cambiar el tamaño del voxel // Si=0  No~=0  :  ');
    
    if op==0
        tvoxel=[];
        tvoxel=f_tvoxel(tvoxel);
    end
end



clc
end