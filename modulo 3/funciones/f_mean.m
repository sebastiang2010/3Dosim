function [Amean,Amin,Amax,s] =f_mean(Phantom,BED,organo)

ind=Phantom==organo;
A=BED(ind);

Amean=mean(A(:));
Amin=min(A(:));
Amax=max(A(:));
s=std(A(:));
end

