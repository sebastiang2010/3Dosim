function I=f_flip(I,flip)

%cell=unique(I(:));
if flip==1;
    %figure(2)
    for i=1:size(I,3)
        I(:,:,i)=flipud(I(:,:,i));
        %imshow(I(:,:,nslice),[]);
        %title(['Slice number # ',num2str(nslice)]);
        %map=jet(length(cell));
        %colormap(map)
        %pause(0.01)
    end
end