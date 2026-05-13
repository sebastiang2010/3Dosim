%PET1=PET1.*n./sum(PET1(:));
PET1=uint16(PET1); 

ok=0; 
if sum(PET1(:))==n;ok=1;end