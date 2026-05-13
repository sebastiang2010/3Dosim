function [I1,BW_skin,BW_fuente] =f_seg_piel(I1)

BW=zeros(size(I1));
I11=I1;
I1=uint8(I1);
% A=(I11>0);
% I11(A)=10;


for i=1:size(I1,3)
    [level,em] = graythresh(I1(:,:,i));
    BW(:,:,i) = im2bw(I1(:,:,i),level);
end
clear I11

BW=uint8(BW);
I1=I1.*BW; 

fill_BW=zeros(size(I1));
for i=1:size(I1,3)
    fill_BW(:,:,i)=imfill(BW(:,:,i),'holes'); 
    %figure(1000)
    %imshow(fill_BW(:,:,i),[])
end

%BW=uint8(BW);
I1=double(I1).*fill_BW; 
%%

BW_skin=zeros(size(I1));
BW_fuente=zeros(size(I1));
figure(200)
for i=1:size(I1,3)
    bw_skin=zeros(size(I1,1),size(I1,2));
    bw_fuente=zeros(size(I1,1),size(I1,2));
    fill_bw=fill_BW(:,:,i);
    %B=[];
    [B,~,N,A]=bwboundaries(fill_bw);
    
    % elimino la fuente en la imagen
    imshow(I1(:,:,i),[]);
    h=title(['Slice number # ',num2str(i)]);
    set(h,'FontWeight','bold')
    hold on
    %     if N>1;
    %         B2=B{2,1};
    %         for j=1:length(B2)
    %             plot(B2(j,2),B2(j,1),'r');
    %         end
    %
    %         bw_fuente(B2(:,1),B2(:,2))=1;
    %     end
    
    for j=1:N;
        %if size(B(1,j))>100;
        [a,b]=size(B{j,1});
        if a>100
            B1=B{j,1};
            for k=1:length(B1)
                bw_skin(B1(k,1),B1(k,2))=1;
                plot(B1(k,2),B1(k,1),'g')
            end
        end
    end
    pause(0.1)
    BW_skin(:,:,i)=bw_skin;
    BW_fuente(:,:,i)=bw_fuente;
end
%%
BW_skin=double(BW_skin);
I1=double(I1);
%I1=I1.~*fill_BW; %para sacar lo que afuera
I1=I1.*~BW_skin;

for i=1:size(I1,3)
    BW_fuente(:,:,i)=imfill(BW_fuente(:,:,i),'holes');
end

I1=I1.*~BW_fuente;

end

