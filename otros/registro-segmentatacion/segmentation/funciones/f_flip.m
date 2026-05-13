function I=f_flip(I,flip)

%cell=unique(I(:));
if flip==1;
    I=I(end:-1:1,:,:); 
    
    %figure(nfig)
%     for i=1:size(I,3)
%         I(:,:,i)=flipud(I(:,:,i));
%         %imshow(I(:,:,nslice),[]);
%         %h=title(['Flip Slice number # ',num2str(nslice)]);
%         %set(h,'FontWeight','bold')
%         %map=jet(length(cell));
%         %colormap(jet)
%         %pause(0.1)
%     end
end