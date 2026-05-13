%prueba sagital coronal 
close all
load mri;
montage(D,map)
title('Horizontal Slices');

M1 = D(:,64,:,:); size(M1)

M2 = reshape(M1,[128 27]); size(M2)
figure, imshow(M2,map);
title('Sagittal - Raw Data');

T0 = maketform('affine',[0 -2.5; 1 0; 0 0]);

R2 = makeresampler({'cubic','nearest'},'fill');
M3 = imtransform(M2,T0,R2);
figure, imshow(M3,map);
title('Sagittal - IMTRANSFORM')

T1 = maketform('affine',[-2.5 0; 0 1; 68.5 0]);
inverseFcn = @(X,t) [X repmat(t.tdata,[size(X,1) 1])];
T2 = maketform('custom',3,2,[],inverseFcn,64);
Tc = maketform('composite',T1,T2);


