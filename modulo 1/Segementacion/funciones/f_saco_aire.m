function [bw_s_aire]=f_saco_aire(I1)

I1 = imadjust(I1,[30000/65535 65535/65535],[]);

BW = imbinarize(I1,'adaptive');

bw_s_aire=imfill(BW,'holes');

% figure(1)
% imshow(fill_bw)

end % function 




