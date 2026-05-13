function [g,Nr,SI,TI]=f_regiongrown_l(f,S,T)

%%pag 409 Gonzalez

f=double(f);
% If S is a scalar, obtein the seed image
if numel(S)==1;
   SI=f==S;
   S1=S;
else 
    %S is array. Eliminate duplicate, connected seed locations
    %to reduce the number of loop execuctions in thje folowing 
    %section of the code.
    SI=f_bwmorph_l(S,'shrink',Inf);
    J=find(SI);
    S1=f(J);
end
   
T1=false(size(f));
for k=1:length(S1)
    seedvalue=S1(K); 
    S=abs(f-seedvalue)<=T;
    TI=TI | S;
end
%Use function 
%
%
[g,NR]=bwlabel(imresconstruct(SI,TI)); 
    
   