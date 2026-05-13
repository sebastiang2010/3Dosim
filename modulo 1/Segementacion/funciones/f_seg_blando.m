function [Phantom1] =f_seg_blando(I1,Phantom1,index_blando)
%figure(71)
for i=1:size(I1,3)
    ind=I1(:,:,i)~=0;
    A=zeros(size(I1,1),size(I1,2));
    A(ind)=index_blando;
    Phantom1(:,:,i)=Phantom1(:,:,i)+A;
    clear A ind
    imshow(Phantom1(:,:,i),[])
    h=title(['Slice number # ',num2str(i)]);
    set(h,'FontWeight','bold')
    colormap(jet)
    pause(0.25)
end


end

