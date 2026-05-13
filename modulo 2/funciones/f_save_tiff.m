function f_save_tiff(I,op,directorio) 

clc
if op==1;file=[directorio,'\PET.tif'];end
if op==0;file=[directorio,'\CT.tif'];end
if op==2;file=[directorio,'\Phantom.tif'];end


% for i=1:size(I,3)
%     imshow(I(:,:,i),[])
%     pause(0.1)
% end 

delete(file);
imwrite(I(:,:,1),file,'tiff','WriteMode','overwrite','Compression','none')
for i=2:size(I,3)
    imwrite(I(:,:,i),file,'tiff','WriteMode','append','Compression','none')
end
disp('.......')
disp(['Se grabo la imagen]',file,'  en D:\MAT\3Dosim\'])